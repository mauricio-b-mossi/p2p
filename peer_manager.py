# manages peer connections, runs timers.
import time
import threading
import random
from logger import log_preferred_neighbors, log_optimistic_neighbor


class PeerManager:
    """
    Manages all connections and runs the choking/unchoking logic.
    """

    def __init__(self, my_peer_id, file_manager, common_config):
        self.my_peer_id = my_peer_id
        self.file_manager = file_manager

        self.k = int(common_config["NumberOfPreferredNeighbors"])
        self.p_interval = int(common_config["UnchokingInterval"])
        self.m_interval = int(common_config["OptimisticUnchokingInterval"])

        # --- State tracking ---
        # This will map peer_id -> ConnectionHandler thread
        self.connections = {}
        self.preferred_neighbors = set()
        self.optimistic_neighbor = None

        # Recommended to lock by GPT
        self.lock = threading.Lock()

        print(
            f"[{my_peer_id}] PeerManager initialized (k={self.k}, p={self.p_interval}, m={self.m_interval})."
        )

    def add_connection(self, peer_id, handler_thread):
        """
        Called by the main process when a new
        connection (in or out) is successful.
        """
        with self.lock:
            self.connections[peer_id] = handler_thread
        print(f"[{self.my_peer_id}] PeerManager registered connection with {peer_id}.")

    def remove_connection(self, peer_id):
        """
        Called by a ConnectionHandler when its
        about to terminate.
        """
        with self.lock:
            if peer_id in self.connections:
                del self.connections[peer_id]
            self.preferred_neighbors.discard(peer_id)
            if self.optimistic_neighbor == peer_id:
                self.optimistic_neighbor = None
        print(f"[{self.my_peer_id}] PeerManager removed connection with {peer_id}.")

    def start_timers(self):
        """
        Starts the two main timers for choking and
        optimistic unchoking in their own threads.
        """
        threading.Thread(target=self._preferred_neighbor_timer, daemon=True).start()
        threading.Thread(target=self._optimistic_neighbor_timer, daemon=True).start()

    def _preferred_neighbor_timer(self):
        """
        Timer that runs every p seconds to
        reselect preferred neighbors.
        """
        while True:
            time.sleep(self.p_interval)

            # Ok this is complex
            with self.lock:
                # First we get all interested neighbors
                interested_peers = []
                for peer_id, handler in self.connections.items():
                    if handler.is_interested_in_me:
                        # We also need their download rate
                        rate = handler.get_download_rate()
                        interested_peers.append((rate, peer_id))

                # We sort based on download rate
                interested_peers.sort(key=lambda x: x[0], reverse=True)

                # easy just select top k
                new_preferred_set = {
                    peer_id for rate, peer_id in interested_peers[: self.k]
                }

                # TODO: If we have the *complete file*, select randomly from all interested peers

                peers_to_unchoke = new_preferred_set - self.preferred_neighbors
                peers_to_choke = self.preferred_neighbors - new_preferred_set

                # send choke and unchoke messages
                for peer_id in peers_to_unchoke:
                    if self.connections[peer_id].am_choking_them:
                        self.connections[peer_id].send_unchoke()

                for peer_id in peers_to_choke:
                    # carefull... do not  choke the optimistic neighbor
                    if peer_id != self.optimistic_neighbor:
                        if not self.connections[peer_id].am_choking_them:
                            self.connections[peer_id].send_choke()

                # save new state
                self.preferred_neighbors = new_preferred_set
                log_preferred_neighbors(self.my_peer_id, list(new_preferred_set))

    def _optimistic_neighbor_timer(self):
        """
        Timer that runs every 'm' seconds to
        re-select the optimistic neighbor.
        """
        while True:
            time.sleep(self.m_interval)

            # Another complex bit
            with self.lock:
                # Find all interested chocked neighbors
                eligible_peers = []
                for peer_id, handler in self.connections.items():
                    if handler.is_interested_in_me and handler.am_choking_them:
                        eligible_peers.append(peer_id)

                # as in the spec, we randomly select
                if eligible_peers:
                    new_optimistic_neighbor = random.choice(eligible_peers)

                    # Choke the old one is not preferred
                    should_choke_old = (
                        self.optimistic_neighbor
                        and self.optimistic_neighbor not in self.preferred_neighbors
                        and not self.connections[
                            self.optimistic_neighbor
                        ].am_choking_them
                    )

                    if should_choke_old:
                        self.connections[self.optimistic_neighbor].send_choke()

                    # Unchoke the new one
                    self.optimistic_neighbor = new_optimistic_neighbor
                    if self.connections[self.optimistic_neighbor].am_choking_them:
                        self.connections[self.optimistic_neighbor].send_unchoke()

                    log_optimistic_neighbor(self.my_peer_id, self.optimistic_neighbor)
