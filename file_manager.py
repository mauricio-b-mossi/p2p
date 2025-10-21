import os
import math
from bitfield import Bitfield


# This class is a helper to manage files being downloaded/shared.
# It manages the bitfield and the file pieces on disj.
class FileManager:
    def __init__(self, my_peer_info, common_config):
        self.peer_id = my_peer_info.peer_id
        self.file_name = common_config["FileName"]
        self.file_size = int(common_config["FileSize"])
        self.piece_size = int(common_config["PieceSize"])

        # this is determined by config
        self.num_pieces = math.ceil(self.file_size / self.piece_size)

        # --- naming and creating the directory ---

        self.peer_dir = f"peer_{self.peer_id}"

        self.file_path = os.path.join(self.peer_dir, self.file_name)

        os.makedirs(self.peer_dir, exist_ok=True)

        # --- create bitfield for this peer's file ---
        self.bitfield = Bitfield(self.num_pieces)

        if my_peer_info.has_file:
            print(f"[{self.peer_id}] Peer starts with the file.")
            # If we have the file, set all bits in our bitfield to 1
            self.bitfield.set_all()

            # TODO: Verify the file on disk or create it if missing

        else:
            print(f"[{self.peer_id}] Peer starts with no pieces.")
            # TODO: If we don't have the file, ensure any
            # partial file is deleted or handled.

        print(f"[{self.peer_id}] File Manager initialized.")
        print(f"[{self.peer_id}] File: {self.file_name}, Size: {self.file_size}")
        print(
            f"[{self.peer_id}] Piece Size: {self.piece_size}, Num Pieces: {self.num_pieces}"
        )
        print(f"[{self.peer_id}] My Bitfield: {self.bitfield}")
        
    def check_interest(self, their_bitfield):
        return self.bitfield.has_interesting_pieces(their_bitfield)
