import time
import threading
import random
from logger import log_preferred_neighbors, log_optimistic_neighbor


class PeerManager:
    def __init__(self, my_peer_id, file_manager, common_config):
        self.my_peer_id = my_peer_id
        self.file_manager = file_manager
        self.k = int(common_config["NumberOfPreferredNeighbors"])
        self.p_interval = int(common_config["UnchokingInterval"])
        self.m_interval = int(common_config["OptimisticUnchokingInterval"])
        self.connections = {}
        self.preferred_neighbors = set()
        self.optimistic_neighbor = None
        self.lock = threading.Lock()
        print(
            f"[{my_peer_id}] PeerManager initialized (k={self.k}, p={self.p_interval}, m={self.m_interval})."
        )

    def add_connection(self, peer_id, handler_thread):
        with self.lock:
            self.connections[peer_id] = handler_thread
        print(f"[{self.my_peer_id}] PeerManager registered connection with {peer_id}.")

    def remove_connection(self, peer_id):
        with self.lock:
            if peer_id in self.connections:
                del self.connections[peer_id]
            self.preferred_neighbors.discard(peer_id)
            if self.optimistic_neighbor == peer_id:
                self.optimistic_neighbor = None
        print(f"[{self.my_peer_id}] PeerManager removed connection with {peer_id}.")

    def start_timers(self):
        threading.Thread(target=self._preferred_neighbor_timer, daemon=True).start()
        threading.Thread(target=self._optimistic_neighbor_timer, daemon=True).start()

    def _preferred_neighbor_timer(self):
        while True:
            time.sleep(self.p_interval)
            with self.lock:
                interested_peers = []
                for peer_id, handler in self.connections.items():
                    if handler.is_interested_in_me:
                        rate = handler.get_download_rate()
                        interested_peers.append((rate, peer_id))
                interested_peers.sort(key=lambda x: x[0], reverse=True)
                new_preferred_set = {
                    peer_id for rate, peer_id in interested_peers[: self.k]
                }

                if self.file_manager.num_pieces_have == self.file_manager.num_pieces:
                    print(
                        f"[{self.my_peer_id}] (File complete, selecting neighbors randomly)"
                    )
                    interested_ids = [pid for rate, pid in interested_peers]
                    random.shuffle(interested_ids)
                    new_preferred_set = set(interested_ids[: self.k])

                peers_to_unchoke = new_preferred_set - self.preferred_neighbors
                peers_to_choke = self.preferred_neighbors - new_preferred_set

                for peer_id in peers_to_unchoke:
                    if self.connections[peer_id].am_choking_them:
                        self.connections[peer_id].send_unchoke()
                for peer_id in peers_to_choke:
                    if peer_id != self.optimistic_neighbor:
                        if not self.connections[peer_id].am_choking_them:
                            self.connections[peer_id].send_choke()
                self.preferred_neighbors = new_preferred_set
                log_preferred_neighbors(self.my_peer_id, list(new_preferred_set))

    def _optimistic_neighbor_timer(self):
        while True:
            time.sleep(self.m_interval)
            with self.lock:
                eligible_peers = []
                for peer_id, handler in self.connections.items():
                    if (
                        handler.is_interested_in_me
                        and handler.am_choking_them
                        and peer_id not in self.preferred_neighbors
                    ):  # careful.. do not pick preferred neightbor
                        eligible_peers.append(peer_id)

                if eligible_peers:
                    new_optimistic_neighbor = random.choice(eligible_peers)
                    if (
                        self.optimistic_neighbor
                        and self.optimistic_neighbor not in self.preferred_neighbors
                        and not self.connections[
                            self.optimistic_neighbor
                        ].am_choking_them
                    ):
                        self.connections[self.optimistic_neighbor].send_choke()
                    self.optimistic_neighbor = new_optimistic_neighbor
                    if self.connections[self.optimistic_neighbor].am_choking_them:
                        self.connections[self.optimistic_neighbor].send_unchoke()
                    log_optimistic_neighbor(self.my_peer_id, self.optimistic_neighbor)

    # Broadcasts to all pieces what current pieces it has
    def broadcast_have(self, piece_index):
        print(f"[{self.my_peer_id}] Broadcasting HAVE {piece_index} to all peers.")
        with self.lock:
            for peer_id, handler in self.connections.items():
                handler.send_have(piece_index)
