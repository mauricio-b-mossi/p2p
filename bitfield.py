import math


# Manager for bitfield as a byte array, helper to work with bitfield.
class Bitfield:
    def __init__(self, num_pieces):

        num_bytes = math.ceil(num_pieces / 8)

        self.field = bytearray(num_bytes)  # initialized bitfield to zeros.
        self.num_pieces = num_pieces

    def set_piece(self, piece_index):
        """
        Sets the bit for a specific piece_index to 1 (meaning we have it).
        """
        if piece_index >= self.num_pieces:
            raise IndexError("Piece index out of bounds")

        byte_index = piece_index // 8
        bit_index_in_byte = piece_index % 8

        # ref pag 7
        #
        # The spec says the first bit in the byte is the high bit.
        # So, we use a mask (128 >> bit_index_in_byte), examples:
        # - index 0 = 10000000 (128)
        # - index 1 = 01000000 (64)
        # ...
        # - index 7 = 00000001 (1)
        mask = 128 >> bit_index_in_byte
        self.field[byte_index] |= mask  # Help GPT

    # Checks for pieces
    def has_piece(self, piece_index):
        if piece_index >= self.num_pieces:
            raise IndexError("Piece index out of bounds")

        byte_index = piece_index // 8
        bit_index_in_byte = piece_index % 8

        mask = 128 >> bit_index_in_byte

        return (self.field[byte_index] & mask) != 0

    def set_all(self):

        self.field = bytearray([255] * len(self.field))

        # claer any spare bits at the end
        spare_bits = (len(self.field) * 8) - self.num_pieces
        if spare_bits > 0:
            last_byte_index = len(self.field) - 1
            mask = 255 << spare_bits
            self.field[last_byte_index] &= mask

    def to_bytes(self):
        return bytes(self.field)

    # class methods came in clutch. Could still use static.
    @classmethod
    def from_bytes(cls, num_pieces, byte_data):
        bitfield = cls(num_pieces)
        if len(byte_data) != len(bitfield.field):
            raise ValueError("Invalid bitfield byte length")
        bitfield.field = bytearray(byte_data)
        return bitfield

    def __str__(self):
        s = ""
        for byte in self.field:
            s += f"{byte:08b} "
        return s.strip()
