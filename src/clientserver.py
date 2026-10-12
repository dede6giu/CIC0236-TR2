import socket
import time
import configurations as cfg
import util

def make_socket() -> socket:
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    clientSocket.settimeout(cfg.basetimeout)
    return clientSocket

def close_socket(clientSocket: socket) -> None:
    clientSocket.close()
    return

def send_pick_header(clientSocket: socket, pacote: str) -> (str, bytes, float):
    """
        clientSocket:socket socket
        pacote:str          pacote para enviar
    ->  (str, bytes, float) (return message, returning data, RTT)

    Envia uma mensagem para o servidor.
    Em timeout, retorna ("TIMEOUT", ..., ...)
    """
    try:
        rawdata, RTT = send_message(clientSocket, pacote)
    except socket.timeout:
        return ("TIMEOUT", b"msg=Socket timeout", 0)
    rtrnMsg, data = util.get_return_type(rawdata)
    return (rtrnMsg, data, RTT) 

def send_message(clientSocket: socket, pacote: str) -> (bytes, float):
    """
        clientSocket:socket socket
        pacote:str          pacote para enviar
    ->  (bytes, float)      (returning data, RTT)

    Envia uma mensagem para o servidor.
    Erro socket.timeout se ocorrer timeout.
    """

    # Enviar mensagem
    timeStart = time.time()
    clientSocket.sendto(pacote.encode(cfg.encoding), cfg.server)

    # Nota: talvez timeout, levanta socket.timeout
    rawdata, flags = clientSocket.recvfrom(cfg.pcksize)
    timeEnd = time.time()
    return (rawdata, timeEnd-timeStart)

def handshake(clientSocket: socket) -> str:
    """
    ->  bool    sucesso do handshake? 

    Realiza o handshake entre cliente<->servidor.
    Retorna se deu sucesso.
    """
    # Preparar HELLO
    pacote = "HELLO|"
    pacote += f"grupo={cfg.grupo}|"
    pacote += f"segment_size={cfg.seqSizeDefault}|"
    pacote += f"file={cfg.filetype}"
    
    # Enviar HELLO
    rtrnMsg, rawdata, RTT = send_pick_header(clientSocket, pacote)
    data = util.get_meta_until(rawdata)

    if rtrnMsg == "OK":
        # print(rawdata.decode(cfg.encoding))
        cfg.filesize = int(data["file_size"])
        cfg.checksum = data["checksum"]
        cfg.seed = data["seed"]
        cfg.seqTotalAmount = int(data["total_segments"])
        cfg.seqSize = int(data["segment_size"])
        return "OK"
    elif rtrnMsg == "TIMEOUT":
        return "TIMEOUT"
    else:
        return "ERROR"

def fin(clientSocket: socket, checksum: str) -> str:
    """
        checksum:str    Checksum para enviar ao servidor
    ->  str             Integridade do arquivo

    Envia FIN ao servidor, e já retorna o valor da resposta DONE
    do servidor. Tenta restransmissões de acordo com cfg.maxRetries,
    se falhar nisso retornará False
    """

    pacote = f"FIN|checksum={checksum}"
    
    attempts = 0
    while attempts < cfg.maxRetries:
        rtrnMsg, rawdata, RTT = send_pick_header(clientSocket, pacote)
        if rtrnMsg == "DONE":
            break
        attempts += 1
    else:
        return rtrnMsg

    data = util.get_meta_until(rawdata)
    return "SUCCESS" if int(data["ok"]) == 1 else "FAIL"