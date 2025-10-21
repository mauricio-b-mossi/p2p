# dot source to run commands . ./scripts.ps1
function Create-File{
    param (
    [string]$Name,
    [string]$Length
    )

    fsutil file createnew $Name $Length
}

function Clean-PeerDirectory{
    Get-ChildItem -Exclude peer_7001, peer_1001 | ?{$_.Name -like "peer_?00?"} | Remove-Item -Force -Recurse
}

function Clean-PeerLog{
    Remove-Item log_peer_????.log
}


# --- IF ZOMBIE PROCESS ---
# (base) PS C:\Users\mauri\p2p> netstat -aon | findstr :7003
# TCP    0.0.0.0:7003           0.0.0.0:0              LISTENING       11512
# (base) PS C:\Users\mauri\p2p> Stop-Process -Id 11512 -Force