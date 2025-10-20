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


# Represnets the actual message after the initial handshake.
#
# - Handles creation and parsing of 5 byte header.
class Message:

    CHOKE = 0
    UNCHOKE = 1
    INTERESTED = 2
    NOT_INTERESTED = 3
    HAVE = 4
    BITFIELD = 5
    REQUEST = 6
    PIECE = 7

    def __init__(self, msg_type, payload=b""):
        self.msg_type = msg_type
        self.payload = payload

        # Length is 1 byte for type + length of payload
        self.msg_length = 1 + len(payload)

    def to_bytes(self):
        # Again, at the suggestion of GPT
        # '!I' = 4-byte big-endian integer (for length)
        # '!B' = 1-byte unsigned char (for type)
        return struct.pack("!IB", self.msg_length, self.msg_type) + self.payload

    @staticmethod
    def create_bitfield_message(bitfield):
        return Message(Message.BITFIELD, bitfield.to_bytes())

    def __str__(self):
        # A helper for debugging
        type_names = [
            "CHOKE",
            "UNCHOKE",
            "INTERESTED",
            "NOT_INTERESTED",
            "HAVE",
            "BITFIELD",
            "REQUEST",
            "PIECE",
        ]
        return f"[Msg: {type_names[self.msg_type]}, Len: {self.msg_length}]"
