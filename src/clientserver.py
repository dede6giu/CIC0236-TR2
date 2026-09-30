import socket
import time
import configurations as cfg

def send_message(pacote: str) -> (bytes, int):
    """
        pacote:str    packet to send
    ->  (bytes, int)  (returning data, RTT)

    Sends a message to the server.
    If timeout occurs, raises socket.timeout
    """

    # Socket setup
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    clientSocket.settimeout(cfg.timeout)

    # Send message
    timeStart = time.time()
    clientSocket.sendto(pacote.encode(cfg.encoding), cfg.server)

    # Note: this may timeout, raise socket.timeout
    data, flags = clientSocket.recvfrom(cfg.pcksize)
    timeEnd = time.time()
    rawdata = data
    return (data, timeEnd-timeStart)