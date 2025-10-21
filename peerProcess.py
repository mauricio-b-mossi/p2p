import sys
import re
import socket
import threading
import time

import struct

# --- Local Imports ----
from peer import Peer
from logger import setup_logging, log_tcp_connection_to, log_tcp_connection_from
from message import Handshake, Message
from file_manager import FileManager
from bitfield import Bitfield

# --- Config Parsing ----


def read_common_config():
    try:
        config = open("Common.cfg", "r")
        config_dict = {}
        for line in config:
            match = re.findall(r"(\S+)", line)
            if match:
                config_dict[match[0]] = match[1]
        config.close()
        return config_dict
    except FileNotFoundError:
        print("FATAL ERROR: Common.cfg not found.")
        sys.exit(1)


def read_peer_info_config():
    try:
        config = open("PeerInfo.cfg", "r")
        peer_list = []
        for line in config:
            match = re.findall(r"(\S+)", line)
            if match:
                current_peer = Peer(match[0], match[1], match[2], match[3])
                peer_list.append(current_peer)
        config.close()
        return peer_list
    except FileNotFoundError:
        print("FATAL ERROR: PeerInfo.cfg not found.")
        sys.exit(1)


# --- Manages the peer


def handle_connection(conn_socket, my_peer_id, expected_peer_id, file_manager):
    """
    This function is run in a thread for EVERY connection.
    - file_manager: Our peer's file manager object.
    """
    # --- handshake ----
    other_peer_id = None
    try:
        print(f"[{my_peer_id}] Sending handshake...")
        my_handshake = Handshake(my_peer_id)
        conn_socket.sendall(my_handshake.to_bytes())

        received_handshake_bytes = conn_socket.recv(32)
        if not received_handshake_bytes:
            raise Exception("Connection closed before handshake.")

        received_handshake = Handshake.from_bytes(received_handshake_bytes)
        other_peer_id = received_handshake.peer_id

        if expected_peer_id is not None and other_peer_id != expected_peer_id:
            raise Exception(
                f"Expected peer {expected_peer_id} but got {other_peer_id}."
            )

        print(f"[{my_peer_id}] Handshake successful with peer {other_peer_id}.")

        # --- log connection ---

        if expected_peer_id is not None:
            log_tcp_connection_to(my_peer_id, other_peer_id)
        else:
            log_tcp_connection_from(my_peer_id, other_peer_id)

        # --- bitfield exchange ---

        # sending our bitfield
        print(f"[{my_peer_id}] Sending bitfield to {other_peer_id}...")
        bitfield_msg = Message.create_bitfield_message(file_manager.bitfield)
        conn_socket.sendall(bitfield_msg.to_bytes())

        # receiving their bitfield

        # Reading according to protocol ref pag 7.
        # First, read the 5-byte message header (4-byte len + 1-byte type)
        header_bytes = conn_socket.recv(5)
        if not header_bytes:
            raise Exception(f"Connection with {other_peer_id} closed before bitfield.")

        msg_length, msg_type = struct.unpack("!IB", header_bytes)

        payload_length = msg_length - 1

        # Read the rest of the message
        payload_bytes = conn_socket.recv(payload_length)
        if not payload_bytes:
            raise Exception(f"Connection with {other_peer_id} closed during bitfield.")

        if msg_type != Message.BITFIELD:
            # The spec says bitfield is always the first message (ref pag 2)
            raise Exception(f"Expected BITFIELD (5), but got {msg_type}.")

        # parse their bitfield
        their_bitfield = Bitfield.from_bytes(file_manager.num_pieces, payload_bytes)
        print(
            f"[{my_peer_id}] Received bitfield from {other_peer_id}: {their_bitfield}"
        )

        # TODO: Store this 'their_bitfield' object, associating it
        # with this specific 'other_peer_id' for later use.

        # Send Interested or Not Interested
        # TODO: Compare 'their_bitfield' with 'file_manager.bitfield'
        # and send an 'INTERESTED' or 'NOT_INTERESTED' message.
        print(f"[{my_peer_id}] Sending NOT_INTERESTED (for now) to {other_peer_id}.")
        not_interested_msg = Message(Message.NOT_INTERESTED)
        conn_socket.sendall(not_interested_msg.to_bytes())

        # TODO: Implement message loop.
        while True:
            # before implementing loop, just keep the connection alive
            time.sleep(1)

    except Exception as e:
        if other_peer_id:
            print(f"[{my_peer_id}] Error in connection with {other_peer_id}: {e}")
        else:
            print(f"[{my_peer_id}] Connection failed: {e}")
    finally:
        conn_socket.close()
        if other_peer_id:
            print(f"[{my_peer_id}] Connection with {other_peer_id} closed.")


def start_server(my_peer_id, my_port, file_manager):

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind(("0.0.0.0", my_port))  # wildcard port
        server_socket.listen(10)
        print(f"[{my_peer_id}] Server listening on port {my_port}...")

        while True:
            conn, addr = server_socket.accept()
            print(f"[{my_peer_id}] Accepted connection from {addr}")

            thread = threading.Thread(
                target=handle_connection,
                # Pass the file_manager to the handler
                args=(conn, my_peer_id, None, file_manager),
                daemon=True,
            )
            thread.start()

    except Exception as e:
        print(f"[{my_peer_id}] SERVER ERROR: {e}")
    finally:
        server_socket.close()


if __name__ == "__main__":

    # 1. Parse args and configs
    if len(sys.argv) != 2:
        print("FATAL ERROR: Missing peer ID argument.")
        sys.exit(1)
    try:
        my_peer_id = int(sys.argv[1])
    except ValueError:
        print("FATAL ERROR: Peer ID must be an integer.")
        sys.exit(1)

    print(f"[{my_peer_id}] Starting...")
    common_config = read_common_config()
    all_peers = read_peer_info_config()

    # 2. Find our info
    my_peer_info = None
    peers_to_connect_to = []
    for peer in all_peers:
        if peer.peer_id == my_peer_id:
            my_peer_info = peer
            break
        else:
            peers_to_connect_to.append(peer)

    if my_peer_info is None:
        print(f"FATAL ERROR: Peer ID {my_peer_id} not found in PeerInfo.cfg.")
        sys.exit(1)

    # 3. Setup Logger
    setup_logging(my_peer_id)
    print(f"[{my_peer_id}] Logging to log_peer_{my_peer_id}.log")

    # 4. Initialize File Manager
    file_manager = FileManager(my_peer_info, common_config)

    # 5. Start the Server Thread
    server_thread = threading.Thread(
        target=start_server,
        # Pass the file_manager to the server
        args=(my_peer_info.peer_id, my_peer_info.port, file_manager),
        daemon=True,
    )
    server_thread.start()

    # 6. Start Client Connections
    print(
        f"[{my_peer_id}] Attempting to connect to {len(peers_to_connect_to)} earlier peers..."
    )
    for peer_to_connect in peers_to_connect_to:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_host = "127.0.0.1"

            print(
                f"[{my_peer_id}] Connecting to {peer_to_connect.peer_id} at {target_host}:{peer_to_connect.port}..."
            )
            client_socket.connect((target_host, peer_to_connect.port))
            print(
                f"[{my_peer_id}] Successfully connected to {peer_to_connect.peer_id}."
            )

            thread = threading.Thread(
                target=handle_connection,
                # Pass the file_manager to the handler
                args=(client_socket, my_peer_id, peer_to_connect.peer_id, file_manager),
                daemon=True,
            )
            thread.start()

        except Exception as e:
            print(f"[{my_peer_id}] Failed to connect to {peer_to_connect.peer_id}: {e}")
            client_socket.close()

    print(f"[{my_peer_id}] Startup complete. Running...")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        print(f"\n[{my_peer_id}] Shutting down.")
