import sys
import re
import socket
import threading
import time
import struct
import queue

from peer import Peer
from logger import *
from message import Handshake, Message
from file_manager import FileManager
from bitfield import Bitfield

from peer_manager import PeerManager

PEER_CONFIG_FILE = "HelloWorldCommon.cfg"
# PEER_CONFIG_FILE = "Common.cfg"
PEER_INFO_FILE = "PeerInfo.cfg"


def read_common_config():
    try:
        config = open(PEER_CONFIG_FILE, "r")
        config_dict = {}
        for line in config:
            match = re.findall(r"(\S+)", line)
            if match:
                config_dict[match[0]] = match[1]
        config.close()
        return config_dict
    except FileNotFoundError:
        print(f"FATAL ERROR: {PEER_CONFIG_FILE} not found.")
        sys.exit(1)


def read_peer_info_config():
    try:
        config = open(PEER_INFO_FILE, "r")
        peer_list = []
        for line in config:
            match = re.findall(r"(\S+)", line)
            if match:
                current_peer = Peer(match[0], match[1], match[2], match[3])
                peer_list.append(current_peer)
        config.close()
        return peer_list
    except FileNotFoundError:
        print(f"FATAL ERROR: {PEER_INFO_FILE} not found.")
        sys.exit(1)


# Replaces old handle connection func, this is a THREAD
# that manages a single connection to anther peer.
class ConnectionHandler(threading.Thread):

    def __init__(
        self, conn_socket, my_peer_id, peer_manager, file_manager, expected_peer_id=None
    ):
        super().__init__(daemon=True)
        self.conn_socket = conn_socket
        self.my_peer_id = my_peer_id
        self.peer_manager = peer_manager
        self.file_manager = file_manager

        self.expected_peer_id = expected_peer_id
        self.other_peer_id = None
        self.their_bitfield = Bitfield(file_manager.num_pieces)

        self.am_choking_them = True  # assume we are choking everyone
        self.am_interested_in_them = False
        self.they_are_choking_me = True  # assume they are choking us
        self.is_interested_in_me = False

        self.start_time = time.time()
        self.bytes_downloaded = 0

        self.requested_pieces = set()  # just to ensure we dont request
        # same piece multiple times

    def get_download_rate(self):
        duration = time.time() - self.start_time
        if duration == 0:
            return 0
        rate = self.bytes_downloaded / duration

        self.bytes_downloaded = 0
        self.start_time = time.time()
        return rate

    def run(self):
        try:
            my_handshake = Handshake(self.my_peer_id)
            self.conn_socket.sendall(my_handshake.to_bytes())

            received_bytes = self.conn_socket.recv(32)
            if not received_bytes:
                raise Exception("Connection closed before handshake.")

            received_handshake = Handshake.from_bytes(received_bytes)
            self.other_peer_id = received_handshake.peer_id

            if (
                self.expected_peer_id is not None
                and self.other_peer_id != self.expected_peer_id
            ):
                raise Exception(
                    f"Expected peer {self.expected_peer_id} but got {self.other_peer_id}."
                )

            print(
                f"[{self.my_peer_id}] Handshake successful with {self.other_peer_id}."
            )

            # REgister with peer manager after we know ID
            self.peer_manager.add_connection(self.other_peer_id, self)

            if self.expected_peer_id is not None:
                log_tcp_connection_to(self.my_peer_id, self.other_peer_id)
            else:
                log_tcp_connection_from(self.my_peer_id, self.other_peer_id)

            # Exchange bitfield
            bitfield_msg = Message.create_bitfield_message(self.file_manager.bitfield)
            self.conn_socket.sendall(bitfield_msg.to_bytes())

            bitfield_msg = Message.read_from_socket(self.conn_socket)
            if bitfield_msg is None or bitfield_msg.msg_type != Message.BITFIELD:
                raise Exception("Did not receive bitfield after handshake.")

            self.their_bitfield = Bitfield.from_bytes(
                self.file_manager.num_pieces, bitfield_msg.payload
            )
            print(f"[{self.my_peer_id}] Received bitfield from {self.other_peer_id}.")

            # Reply with interested or not
            if self.file_manager.check_interest(self.their_bitfield):
                self.am_interested_in_them = True
                self.conn_socket.sendall(Message.create_interested_message().to_bytes())
            else:
                self.am_interested_in_them = False
                self.conn_socket.sendall(
                    Message.create_not_interested_message().to_bytes()
                )

            # New main loop
            while True:
                msg = Message.read_from_socket(self.conn_socket)
                if msg is None:
                    print(
                        f"[{self.my_peer_id}] Peer {self.other_peer_id} closed connection."
                    )
                    break

                # --- Handle the message ---
                self.handle_message(msg)

            # --- MAIN LOOP ---
            # while True:
            #     msg = Message.read_from_socket(self.conn_socket)
            #     if msg is None:
            #         print(
            #             f"[{self.my_peer_id}] Peer {self.other_peer_id} closed connection."
            #         )
            #         break

            #     # Handle message
            #     self.handle_message(msg)

        # Error handling courtesy of GPT
        except (IOError, socket.error) as e:
            print(f"[{self.my_peer_id}] Socket error with {self.other_peer_id}: {e}")
        except Exception as e:
            print(
                f"[{self.my_peer_id}] Error in connection with {self.other_peer_id}: {e}"
            )
        finally:
            self.conn_socket.close()
            self.peer_manager.remove_connection(self.other_peer_id)
            print(f"[{self.my_peer_id}] Connection with {self.other_peer_id} closed.")

    def handle_message(self, msg):
        """
        Dispatcher for all incoming messages.
        """
        print(f"[{self.my_peer_id}] Received {msg} from {self.other_peer_id}.")

        if msg.msg_type == Message.CHOKE:
            log_choking(self.my_peer_id, self.other_peer_id)
            self.they_are_choking_me = True

        elif msg.msg_type == Message.UNCHOKE:
            log_unchoking(self.my_peer_id, self.other_peer_id)
            self.they_are_choking_me = False
            # TODO: Pick a piece and send a REQUEST

        elif msg.msg_type == Message.INTERESTED:
            log_receive_interested(self.my_peer_id, self.other_peer_id)
            self.is_interested_in_me = True

        elif msg.msg_type == Message.NOT_INTERESTED:
            log_receive_not_interested(self.my_peer_id, self.other_peer_id)
            self.is_interested_in_me = False

        elif msg.msg_type == Message.HAVE:
            piece_index = struct.unpack("!I", msg.payload)[0]
            log_receive_have(self.my_peer_id, self.other_peer_id, piece_index)
            self.their_bitfield.set_piece(piece_index)

            # TODO: Check if we are now interested
            # IMPLEMENTED BUT LEAVE MARKED IN CASE OF ERROR
            if not self.am_interested_in_them:
                if self.file_manager.check_interest(self.their_bitfield):
                    self.am_interested_in_them = True
                    self.send_interested()

        # TODO: Implement this
        # JUST IMPLEMENTED LEAVE
        elif msg.msg_type == Message.REQUEST:
            piece_index = msg.parse_request_payload()
            print(
                f"[{self.my_peer_id}] Received REQUEST for {piece_index} from {self.other_peer_id}."
            )

            # Send the piece if we're not choking them
            if not self.am_choking_them:
                self.send_piece_message(piece_index)
            else:
                print(
                    f"[{self.my_peer_id}] Ignoring REQUEST from {self.other_peer_id} (choked)."
                )

        # TODO: Implement this
        # JUST IMPLEMENTED LEAVE
        elif msg.msg_type == Message.PIECE:
            piece_index, content = msg.parse_piece_payload()
            print(
                f"[{self.my_peer_id}] Received PIECE {piece_index} from {self.other_peer_id}."
            )

            # rm from requested list
            if piece_index in self.requested_pieces:
                self.requested_pieces.remove(piece_index)

            # write data to file and log
            if self.file_manager.write_piece(piece_index, content):
                log_download_piece(
                    self.my_peer_id,
                    self.other_peer_id,
                    piece_index,
                    self.file_manager.num_pieces_have,
                )

                self.peer_manager.broadcast_have(piece_index)

                # check to verify if donwload complete
                if self.file_manager.num_pieces_have == self.file_manager.num_pieces:
                    log_download_complete(self.my_peer_id)

                self.send_request_message()
            else:
                print(
                    f"[{self.my_peer_id}] ERROR: Failed to write piece {piece_index}."
                )

    def send_choke(self):
        self.conn_socket.sendall(Message.create_choke_message().to_bytes())
        self.am_choking_them = True

    def send_unchoke(self):
        self.conn_socket.sendall(Message.create_unchoke_message().to_bytes())
        self.am_choking_them = False

    def send_request_message(self):
        if self.they_are_choking_me:
            return  # cannot request if choked

        # select random piece if not requesting
        piece_index = self.file_manager.bitfield.select_random_piece(
            self.their_bitfield, self.requested_pieces
        )

        if piece_index is not None:
            print(
                f"[{self.my_peer_id}] Requesting piece {piece_index} from {self.other_peer_id}."
            )
            self.requested_pieces.add(piece_index)
            self.conn_socket.sendall(
                Message.create_request_message(piece_index).to_bytes()
            )
        else:
            print(
                f"[{self.my_peer_id}] No pieces to request from {self.other_peer_id}."
            )
            # TODO: We might need to send NOT_INTERESTED here if there's nothing left

    def send_piece_message(self, piece_index):
        """
        Reads a piece from the file and sends it.
        """
        content = self.file_manager.read_piece(piece_index)
        if content:
            print(
                f"[{self.my_peer_id}] Sending PIECE {piece_index} to {self.other_peer_id}."
            )
            self.conn_socket.sendall(
                Message.create_piece_message(piece_index, content).to_bytes()
            )

    def send_choke(self):
        self.conn_socket.sendall(Message.create_choke_message().to_bytes())
        self.am_choking_them = True

    def send_unchoke(self):
        self.conn_socket.sendall(Message.create_unchoke_message().to_bytes())
        self.am_choking_them = False

    def send_have(self, piece_index):
        self.conn_socket.sendall(Message.create_have_message(piece_index).to_bytes())

    def send_interested(self):
        self.conn_socket.sendall(Message.create_interested_message().to_bytes())


# Changed func by using new ConnectionHandler
def start_server(my_peer_id, my_port, peer_manager, file_manager):

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind(("0.0.0.0", my_port))
        server_socket.listen(10)
        print(f"[{my_peer_id}] Server listening on port {my_port}...")

        while True:
            conn, addr = server_socket.accept()
            print(f"[{my_peer_id}] Accepted connection from {addr}")

            # Create and start the new ConnectionHandler thread
            handler = ConnectionHandler(
                conn, my_peer_id, peer_manager, file_manager, None
            )
            handler.start()

    except Exception as e:
        print(f"[{my_peer_id}] SERVER ERROR: {e}")
    finally:
        server_socket.close()


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("FATAL ERROR: Missing peer ID argument.")
        sys.exit(1)
    try:
        my_peer_id = int(sys.argv[1])
    except ValueError:
        print(f"FATAL ERROR: Peer ID must be an integer.")
        sys.exit(1)

    print(f"[{my_peer_id}] Starting...")
    common_config = read_common_config()
    all_peers = read_peer_info_config()

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

    setup_logging(my_peer_id)
    print(f"[{my_peer_id}] Logging to log_peer_{my_peer_id}.log")

    file_manager = FileManager(my_peer_info, common_config)
    peer_manager = PeerManager(my_peer_id, file_manager, common_config)

    server_thread = threading.Thread(
        target=start_server,
        args=(my_peer_id, my_peer_info.port, peer_manager, file_manager),
        daemon=True,
    )
    server_thread.start()

    for peer_to_connect in peers_to_connect_to:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_host = "127.0.0.1"  # For local testing

            print(f"[{my_peer_id}] Connecting to {peer_to_connect.peer_id}...")
            client_socket.connect((target_host, peer_to_connect.port))

            # Create and start the new ConnectionHandler thread (old handle_conenction)
            handler = ConnectionHandler(
                client_socket,
                my_peer_id,
                peer_manager,
                file_manager,
                peer_to_connect.peer_id,
            )
            handler.start()

        except Exception as e:
            print(f"[{my_peer_id}] Failed to connect to {peer_to_connect.peer_id}: {e}")
            client_socket.close()

    print(f"[{my_peer_id}] Starting PeerManager timers...")
    peer_manager.start_timers()

    print(f"[{my_peer_id}] Startup complete. Running...")
    try:
        while True:
            # TODO: Add termination logic
            time.sleep(5)
    except KeyboardInterrupt:
        print(f"\n[{my_peer_id}] Shutting down.")
