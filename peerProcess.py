import sys
import re
import socket
import threading
import time

from peer import Peer
from logger import setup_logging, log_tcp_connection_to, log_tcp_connection_from
from message import Handshake


def read_common_config():
    print("Reading Common.cfg...")
    try:
        config = open("Common.cfg", "r")
        config_dict = {}
        for line in config:
            match = re.findall(r"(\S+)", line)
            if match:
                # remember, entries are of the form:
                # -----------------------------
                # NumberOfPreferredNeighbors    2
                # UnchokingInterval             5
                # OptimisticUnchokingInterval   15
                # FileName                      TheFile.dat
                # FileSize                      10000232
                # PieceSize                     32768
                # -----------------------------
                # thus match[0] = key, match[1] = value
                config_dict[match[0]] = match[1]

        config.close()
        return config_dict
    except FileNotFoundError:
        print("ERROR: Common.cfg not found.")
        sys.exit(1)


def read_peer_info_config():
    print("Reading PeerInfo.cfg...")
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


def handle_connection(conn_socket, my_peer_id, expected_peer_id):
    """
    This function is run in a thread for EVERY connection.
    It handles the complete lifecycle of a connection with another peer.

    - conn_socket: The socket object for this connection.
    - my_peer_id: Our own peer ID.
    - expected_peer_id: The ID we expect from the other peer.
                        If we are the server (listener), this is None.
    """
    other_peer_id = None
    try:
        # 1. --- HANDSHAKE ---
        print(f"[{my_peer_id}] Sending handshake...")
        my_handshake = Handshake(my_peer_id)
        conn_socket.sendall(my_handshake.to_bytes())

        # 2. Receive and parse their handshake
        received_handshake_bytes = conn_socket.recv(32)
        if not received_handshake_bytes:
            raise Exception("Connection closed before handshake.")

        received_handshake = Handshake.from_bytes(received_handshake_bytes)
        other_peer_id = received_handshake.peer_id

        # 3. Validate their handshake
        if expected_peer_id is not None and other_peer_id != expected_peer_id:
            # This happens if we connected TO a peer
            raise Exception(
                f"Expected peer {expected_peer_id} but got {other_peer_id}."
            )

        print(f"[{my_peer_id}] Handshake successful with peer {other_peer_id}.")

        # 4. --- LOG THE CONNECTION ---
        if expected_peer_id is not None:
            # We were the client, so we log "makes a connection to"
            log_tcp_connection_to(my_peer_id, other_peer_id)
        else:
            # We were the server, so we log "is connected from"
            log_tcp_connection_from(my_peer_id, other_peer_id)

        # 5. --- BITFIELD EXCHANGE (Coming in Step 3) ---
        # TODO: Send our bitfield
        # TODO: Receive their bitfield

        # 6. --- MESSAGE LOOP (Coming in Step 4) ---
        while True:
            # For now, just keep the connection alive
            time.sleep(1)

    except Exception as e:
        # If an error happens, log it and close the connection
        if other_peer_id:
            print(f"[{my_peer_id}] Error in connection with {other_peer_id}: {e}")
        else:
            print(f"[{my_peer_id}] Connection failed: {e}")
    finally:
        conn_socket.close()
        if other_peer_id:
            print(f"[{my_peer_id}] Connection with {other_peer_id} closed.")


def start_server(my_peer_id, my_port):
    """
    Starts the server thread to listen for incoming connections.
    """
    # Create a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # This allows us to reuse the address quickly
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        # Bind to '0.0.0.0' to listen on all available interfaces
        # (This is better than '127.0.0.1' for testing across machines)
        server_socket.bind(("0.0.0.0", my_port))
        server_socket.listen(10)  # Listen for up to 10 waiting connections
        print(f"[{my_peer_id}] Server listening on port {my_port}...")

        while True:
            # Wait and accept a new connection
            conn, addr = server_socket.accept()
            print(f"[{my_peer_id}] Accepted connection from {addr}")

            # Create a new thread to handle this connection.
            # We pass expected_peer_id=None because we don't know
            # who is connecting to us until after the handshake.
            thread = threading.Thread(
                target=handle_connection,
                args=(conn, my_peer_id, None),
                daemon=True,  # Dies when the main program exits
            )
            thread.start()

    except Exception as e:
        print(f"[{my_peer_id}] SERVER ERROR: {e}")
    finally:
        server_socket.close()


# Executing program
if __name__ == "__main__":

    # Check if we got ID argument
    if len(sys.argv) != 2:
        print("ERROR: Missing peer ID argument.")
        print("Usage: python peerProcess.py [peerID]")
        sys.exit(1)

    try:
        my_peer_id = int(sys.argv[1])
    except ValueError:
        print("ERROR: Peer ID must be an integer.")
        print("Usage: python peerProcess.py [peerID]")
        sys.exit(1)

    print(f"Starting peer process for peer {my_peer_id}...")

    # Reading config files
    common_config = read_common_config()
    all_peers = read_peer_info_config()

    # Getting/Finding our peer, then connecting to those above/already connected (ref pag 7).
    my_peer_info = None
    peers_to_connect_to = []

    # Note this depends on the order of apperance in the PeerInfo.cfg,
    # we suppose (pag 7) all peers before in file have already connected.
    for peer in all_peers:
        if peer.peer_id == my_peer_id:
            my_peer_info = peer
            break
        else:
            peers_to_connect_to.append(peer)

    if my_peer_info is None:
        print(f"ERROR: Peer ID {my_peer_id} not found in PeerInfo.cfg.")
        print("Add entry to PeerInfo.cfg or check [peerID].")
        sys.exit(1)

    # 3. --- NEW: Setup Logger ---
    setup_logging(my_peer_id)
    print(f"[{my_peer_id}] Logging to log_peer_{my_peer_id}.log")

    # 4. --- NEW: Start the Server Thread ---
    # We must start listening *before* we try to connect to others.
    server_thread = threading.Thread(
        target=start_server,
        args=(my_peer_info.peer_id, my_peer_info.port),
        daemon=True,  # This thread will exit when the main program exits
    )
    server_thread.start()

    # 5. --- NEW: Start Client Connections ---
    print(
        f"[{my_peer_id}] Attempting to connect to {len(peers_to_connect_to)} earlier peers..."
    )
    for peer_to_connect in peers_to_connect_to:
        try:
            # Create a socket to connect
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # NOTE: For real testing, use peer_to_connect.ip_address
            # For local-only testing, use '127.0.0.1'
            target_host = "127.0.0.1"

            print(
                f"[{my_peer_id}] Connecting to {peer_to_connect.peer_id} at {target_host}:{peer_to_connect.port}..."
            )
            client_socket.connect((target_host, peer_to_connect.port))
            print(
                f"[{my_peer_id}] Successfully connected to {peer_to_connect.peer_id}."
            )

            # Start a handler thread for this new connection
            # This time, we *know* who we expect to connect to.
            thread = threading.Thread(
                target=handle_connection,
                args=(client_socket, my_peer_id, peer_to_connect.peer_id),
                daemon=True,
            )
            thread.start()

        except Exception as e:
            print(f"[{my_peer_id}] Failed to connect to {peer_to_connect.peer_id}: {e}")
            client_socket.close()

    print(f"[{my_peer_id}] Startup complete. Running...")
    # The main thread will just sit here.
    # The program will run until you kill it (Ctrl+C)
    # because the server_thread is running.
    try:
        while True:
            time.sleep(5)  # Keep the main thread alive
    except KeyboardInterrupt:
        print(f"\n[{my_peer_id}] Shutting down.")


#   # --- Testing SetUp--- #
#   print("\n--- Common Config ---")
#   for key, value in common_config.items():
#       print(f"{key}: {value}")
#
#   print(f"\n--- My Info ---")
#   print(my_peer_info)
#
#   print(f"\n--- Peers I Will Connect To ---")
#   if not peers_to_connect_to:
#       print("None (I am the first peer)")
#   else:
#       for peer in peers_to_connect_to:
#           print(peer)
#
#   print(f"\nStartup complete. Ready for next step.")
