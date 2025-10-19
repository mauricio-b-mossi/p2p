import sys
import re
from peer import Peer


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

    # --- Testing --- #
    # 4. Print what we've learned (for testing)
    print("\n--- Common Config ---")
    for key, value in common_config.items():
        print(f"{key}: {value}")

    print(f"\n--- My Info ---")
    print(my_peer_info)

    print(f"\n--- Peers I Will Connect To ---")
    if not peers_to_connect_to:
        print("None (I am the first peer)")
    else:
        for peer in peers_to_connect_to:
            print(peer)

    print(f"\nStartup complete. Ready for next step.")
