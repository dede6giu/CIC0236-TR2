import socket
import time
import configurations as cfg

def send_message(pacote: str) -> (bytes, int):
    """
        pacote:str    packet to send
    ->  (bytes, int)  (returning data, RTT)

    Envia uma mensagem para o servidor.
    Erro socket.timeout se ocorrer timeout.
    """

    # Socket setup
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    clientSocket.settimeout(cfg.timeout)

    # Enviar mensagem
    timeStart = time.time()
    clientSocket.sendto(pacote.encode(cfg.encoding), cfg.server)

    # Nota: talvez timeout, levanta socket.timeout
    data, flags = clientSocket.recvfrom(cfg.pcksize)
    timeEnd = time.time()
    rawdata = data
    return (data, timeEnd-timeStart)