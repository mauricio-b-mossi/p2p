import logging
import datetime

# We'll use a single, global logger object
peer_logger = logging.getLogger("p2p")
is_setup = False


def setup_logging(peer_id):
    """
    Configures the logger to write to the correct file.
    """
    global is_setup
    if is_setup:
        return

    log_file = f"log_peer_{peer_id}.log"
    peer_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(log_file, mode="w")
    formatter = logging.Formatter(
        "%(asctime)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    peer_logger.addHandler(handler)
    is_setup = True


# --- Refer to format pag 9 ---


def log_tcp_connection_to(my_id, other_id):
    peer_logger.info(f"Peer {my_id} makes a connection to Peer {other_id}.")


def log_tcp_connection_from(my_id, other_id):
    peer_logger.info(f"Peer {my_id} is connected from Peer {other_id}.")


def log_preferred_neighbors(my_id, neighbor_ids):
    # [Time]: Peer [peer_ID] has the preferred neighbors [preferred neighbor ID list].
    if not neighbor_ids:
        neighbor_list = "[]"
    else:
        neighbor_list = ",".join(map(str, neighbor_ids))
    peer_logger.info(f"Peer {my_id} has the preferred neighbors [{neighbor_list}].")


def log_optimistic_neighbor(my_id, neighbor_id):
    # [Time]: Peer [peer_ID] has the optimistically unchoked neighbor [optimistically unchoked neighbor ID].
    peer_logger.info(
        f"Peer {my_id} has the optimistically unchoked neighbor {neighbor_id}."
    )


def log_unchoking(my_id, other_id):
    # [Time]: Peer [peer_ID 1] is unchoked by [peer_ID 2].
    peer_logger.info(f"Peer {my_id} is unchoked by {other_id}.")


def log_choking(my_id, other_id):
    # [Time]: Peer [peer_ID 1] is choked by [peer_ID 2].
    peer_logger.info(f"Peer {my_id} is choked by {other_id}.")


def log_receive_have(my_id, other_id, piece_index):
    # [Time]: Peer [peer_ID 1] received the 'have' message from [peer_ID 2] for the piece [piece index].
    peer_logger.info(
        f"Peer {my_id} received the 'have' message from {other_id} for the piece {piece_index}."
    )


def log_receive_interested(my_id, other_id):
    # [Time]: Peer [peer_ID 1] received the 'interested' message from [peer_ID 2].
    peer_logger.info(f"Peer {my_id} received the 'interested' message from {other_id}.")


def log_receive_not_interested(my_id, other_id):
    # [Time]: Peer [peer_ID 1] received the 'not interested' message from [peer_ID 2].
    peer_logger.info(
        f"Peer {my_id} received the 'not interested' message from {other_id}."
    )


def log_download_piece(my_id, other_id, piece_index, num_pieces):
    # [Time]: Peer [peer_ID 1] has downloaded the piece [piece index] from [peer_ID 2]. Now the number of pieces it has is [number of pieces].
    peer_logger.info(
        f"Peer {my_id} has downloaded the piece {piece_index} from {other_id}. Now the number of pieces it has is {num_pieces}."
    )


def log_download_complete(my_id):
    # [Time]: Peer [peer_ID] has downloaded the complete file.
    peer_logger.info(f"Peer {my_id} has downloaded the complete file.")
