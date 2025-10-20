class Peer:  # could rewrite as @dataclass
    def __init__(self, peer_id, ip_address, port, has_file):
        self.peer_id = int(peer_id)
        self.ip_address = ip_address
        self.port = int(port)
        self.has_file = bool(int(has_file))

        self.bitfield = None

    def __str__(self):
        return f"Peer(ID: {self.peer_id}, Addr: {self.ip_address}:{self.port}, HasFile: {self.has_file})"
