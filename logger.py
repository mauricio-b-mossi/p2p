# ref pag 9 for logging info
import logging
import datetime

# Global log object
peer_logger = logging.getLogger("p2p")


def setup_logging(peer_id):

    log_file = f"log_peer_{peer_id}.log"

    # Levels are debug, info, warning, error, critical.
    # This determines at what log level we are logging.
    peer_logger.setLevel(logging.INFO)

    # NOTE: We overwrite the old log_file.
    handler = logging.FileHandler(log_file, mode="w")

    # Time will be automatically set on each log.
    formatter = logging.Formatter(
        "%(asctime)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    # Add the handler to the logger (configures format)
    peer_logger.addHandler(handler)


# ---------- TCP connection ----------


# Logs when we (my_id) make a connection TO another peer (other_id).
# Message should look like:
# ----------------------------------------------------------------
# [Time]: Peer [peer_ID 1] makes a connection to Peer [peer_ID 2].
# ----------------------------------------------------------------
def log_tcp_connection_to(my_id, other_id):
    peer_logger.info(f"Peer {my_id} makes a connection to Peer {other_id}.")


# Logs when another peer (other_id) connects FROM us (my_id).
# Message should look like:
# ----------------------------------------------------------------
# [Time]: Peer [peer_ID 1] is connected from Peer [peer_ID 2].
# ----------------------------------------------------------------
def log_tcp_connection_from(my_id, other_id):
    peer_logger.info(f"Peer {my_id} is connected from Peer {other_id}.")


# ---------- change or preferred neighbors ----------

# ---------- change of optimistically unchoked neighbor ----------

# ---------- unchoking ----------

# ---------- choking ----------

# ---------- receiving 'have' message ----------

# ---------- receiving 'interested' message ----------

# ---------- receiving 'not interested' message ----------

# ---------- downloading a piece ----------

# ---------- completion of download ----------
