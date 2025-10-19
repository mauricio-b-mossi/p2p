# ref pag 1 protocol description
import struct


# Class to manage creation and parsing of Handshake message.
# - to_bytes: Converts interal representation into 32-byte handshake message.
# - from_bytes: Parses 32-byte message and returns Handshake object OR raises if invalid.
#
#     ---------------------------------------------------------
#    | P2PFILESHARINGPROJ | 10 empty bytes (\x00) | 4 byte pid |
#     ---------------------------------------------------------
#
class Handshake:

    HEADER = b"P2PFILESHARINGPROJ"

    def __init__(self, peer_id):
        # could check if 4 byte pid
        self.peer_id = peer_id

    def to_bytes(self):
        zero_bits = bytes(10)  # 10-byte zero bits

        # NOTE: '!' means network (big-endian) byte order and 'I' means 4-byte unsigned integer.
        peer_id_bytes = struct.pack("!I", self.peer_id)

        return self.HEADER + zero_bits + peer_id_bytes

    @staticmethod
    def from_bytes(message_bytes):
        if len(message_bytes) != 32:
            raise ValueError("Handshake message must be 32 bytes long.")

        # Help of GPT:
        # Unpack the header and peer ID
        # '18s' = 18-byte string
        # '10x' = 10 "padding" bytes (we ignore them)
        # '!I'  = 4-byte big-endian unsigned integer
        header, peer_id = struct.unpack("!18s10xI", message_bytes)

        if header != Handshake.HEADER:
            raise ValueError(f"Invalid handshake header. Got: {header}")

        return Handshake(peer_id)
