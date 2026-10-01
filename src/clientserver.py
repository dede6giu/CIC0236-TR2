import socket
import time
import configurations as cfg
import util

def send_pick_header(pacote) -> (str, bytes, int):
    """
        pacote:str          pacote para enviar
    ->  (str, bytes, int)   (return message, returning data, RTT)

    Envia uma mensagem para o servidor.
    Em timeout, retorna ("Timeout", ..., ...)
    """
    try:
        rawdata, RTT = send_message(pacote)
    except socket.timeout:
        return ("TIMEOUT", "msg=Socket timeout".encode(cfg.encoding), 0)
    rtrnMsg, data = util.get_return_type(rawdata)
    return (rtrnMsg, data, RTT) 

def send_message(pacote: str) -> (bytes, int):
    """
        pacote:str    pacote para enviar
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

def handshake() -> bool:
    """
    ->  bool    sucesso do handshake? 

    Realiza o handshake entre cliente<->servidor.
    Retorna se deu sucesso.
    """
    # Preparar HELLO
    pacote = "HELLO|"
    pacote += f"grupo={cfg.grupo}|"
    pacote += f"segment_size={cfg.defsegsize}|"
    pacote += f"file={cfg.filetype}"
    
    # Enviar HELLO
    rtrnMsg, rawdata, RTT = send_pick_header(pacote)
    data = util.get_meta_until(rawdata)

    if rtrnMsg == "OK":
        cfg.filesize = data["file_size"]
        cfg.checksum = data["checksum"]
        cfg.seed = data["seed"]
        cfg.segqntt = data["total_segments"]
        cfg.segsize = data["segment_size"]
        return True
    else:
        return False