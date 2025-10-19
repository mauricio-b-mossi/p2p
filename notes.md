# Protocol Description
- Uses TCP
- Symmetrical messages (req and response have same format).

Consists of handshake followed by stream of length prefixed messages.
```
                     ------------------
                    | length | payload |
                     ------------------
```
On connect each peer sends a handshake message before sending other messages.

## Handshake message
```
             ---------------------------------------------------------
            | P2PFILESHARINGPROJ | 10 empty bytes (\x00) | 4 byte pid |
             ---------------------------------------------------------
```
After handshake we proceede with the actual message.

## Actual message
```
             -------------------------------------------------------
            | 4 byte message length | 1 byte message type | payload |
             -------------------------------------------------------
```
Thus, the payload can be at most 2^{32} - 2.
- Why 32? Because message length is in bytes, thus 4 bytes = 32 bits.

## Message types

### No payload types
- `(1) choke`
- `(2) unchoke`
- `(3) interested`
- `(4) not interested`

### payload types
- `(5) have`: Has a payload that contains a 4-byte piece index field.
- `(6) bitfield`: Announces as a bitmap which chunks it has.
- `(7) request`: Has a payload that contains a 4-byte piece index field.
- `(8) piece`: Has a payload that contains a 4-byte piece index field and the content of the piece.

# Protocol in Action (Symmetric)
Suppose peer A makes successful TCP connection to peer B.

### handshake and bitfield
After handshake is succesful A and B exchange **bitfield** messages if they 
have pieces.

### choke and unchoke
Peer uploads pieces to at most `k` neighbors and 1 optimistically unchoked neightbor (...).
- `k` is a program parameter, given when the program starts.
- `unchoked`: Neighbors to whom we are transmitting.
- `choked`: Neighbors to whom we are **not** transmitting.

Peer determines preferred neighbors every `p` seconds.
- **preferred neighbors** are the ones who have been sending data at the highest rate (tit-for-tat).
- select `k` such neightbors, break ties randomly.

Once the neighbors have been determined, send **unchoke** messages
and expect **request** messages from them.

All previous unchocked neighbors that are no longer preferred neighbors choke
by sending **choke** message and stop sending pieces to them (unless optimistically unchocked).

If A has complete file, it determines neighbors randomly.

An **optimisically unchocked peer** is a peer selected randomly every `m` seconds
from those interested in the data.

### interested and not interested
- On connect, the **bitfield** message is sent, if the other peer has pieces we dont,
send **interested** message.
- On **have** message, if peer has pieces we dont, send **interested** message.

Each peer mantains bitfields for all neighbors and updates them whenever
it receives **have** messages.

If peer does not have pieces we dont, send **not interested** message.

When a peer completes download, it sends **not interested** messages
to all the peers that had that piece.

### request and piece
When unchocked, peer sends **request** message for the piece it requested.
- Note, the unchoked piece selects the piece randomly in the **request** message.

The server responds to **request** messages with **piece** messages containing the
requested piece. Once received, the client requests another piece, this continues
until the client is choked or the server has no missing pieces. 

- Note, **request** messages might be unanswered given the process is chocked.

# Implementation Specifics
There are two configuration files `Common.cgf` and `PeerInfo.cfg`.
- `Common.cgf`: Holds properties common to all peers.
- `PeerInfo.cgf`: Holds the information for peers.

## Common.cgf: Holds peer properties
```
NumberOfPreferredNeighbors 2        # Number of neighbors (int)
UnchokingInterval 5                 # Interval in seconds
OptimisticUnchokingInterval 15      # Interval in seconds
FileName TheFile.dat                # File to be downloaded
FileSize 10000232                   # File size in bytes
PieceSize 32768                     # Size of a piece in bytes
```

When a peer starts, it should `Common.cfg`.

## PeerInfo.cgf: Illustration of file
1001 lin114-00.cise.ufl.edu 6008 1 
1002 lin114-01.cise.ufl.edu 6008 0  
1003 lin114-02.cise.ufl.edu 6008 0  
1004 lin114-03.cise.ufl.edu 6008 0  
1005 lin114-04.cise.ufl.edu 6008 0  
1006 lin114-05.cise.ufl.edu 6008 0 

Each entry follows the format,
```
[id] [host] [port] [has file?]
```
- Note, we only consider complete files, no partials.

`PeerInfo.cgf` is static, it emulates the BitTorrent tracker. So on start,
it must have all nodes in the system preconfigured.
