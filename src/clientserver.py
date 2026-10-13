import socket
import time
import configurations as cfg
import util
import mensagens as msg

def make_socket() -> socket:
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    clientSocket.settimeout(cfg.baseTimeout)
    return clientSocket

def close_socket(clientSocket: socket) -> None:
    clientSocket.close()
    return

def send_recv(clientSocket: socket, pacote: msg.Pacote) -> msg.Pacote:
    rtrnMsg, data, RTT = send_pick_header(clientSocket, pacote)
    match rtrnMsg:
        case "PONG":
            return msg.Pong(RTT, data)
        case "OK":
            return msg.Ok(RTT, data)
        case "DATA":
            return msg.Data(RTT, data)
        case "DONE":
            return msg.Done(RTT, data)
        case "TIMEOUT":
            return msg.Timeout("Servidor não respondeu")
        case "ERROR":
            return msg.Error(RTT, data)
        case _:
            return msg.Error(-1, b"Resposta desconhecida do servidor")

def send_pick_header(clientSocket: socket, pacote: msg.Pacote) -> (str, bytes, float):
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
        return ("TIMEOUT", b"", -1)
    rtrnMsg, data = util.get_return_type(rawdata)
    return (rtrnMsg, data, RTT) 

def send_message(clientSocket: socket, pacote: msg.Pacote) -> (bytes, float):
    """
        clientSocket:socket socket
        pacote:str          pacote para enviar
    ->  (bytes, float)      (returning data, RTT)

    Envia uma mensagem para o servidor.
    Erro socket.timeout se ocorrer timeout.
    """

    # Enviar mensagem
    timeStart = time.time()
    clientSocket.sendto(str(pacote).encode(cfg.encoding), cfg.server)

    # Nota: talvez timeout, levanta socket.timeout
    rawdata, flags = clientSocket.recvfrom(cfg.pcksize)
    timeEnd = time.time()
    return (rawdata, timeEnd-timeStart)

def handshake(clientSocket: socket) -> msg.Ok|msg.Timeout|msg.Error:
    """
        clientSocket:socket socket
    ->  msg                 retorno do servidor

    Realiza o handshake entre cliente<->servidor.
    Retorna a mensagem do servidor.
    """

    pacote = msg.Hello(
        cfg.grupo,
        cfg.seqSizeDefault,
        cfg.filetype
    )
    srvResponse = send_recv(clientSocket, pacote)
    return srvResponse

def req(clientSocket: socket, seq: int) -> msg.Data|msg.Timeout|msg.Error:
    """
        clientSocket:socket conexão (já com handshake)
        seq:int             número de sequência
    ->  msg                 pacote resultante

    Requisita a sequência seq para o servidor e já retorna o payload
    em caso de sucesso.
    """

    pacote = msg.Req(seq)
    return send_recv(clientSocket, pacote)

def ack(clientSocket: socket, seq: int) -> msg.Error:
    """
        clientSocket:socket conexão (já com handshake)
        seq:int             número de sequência
    ->  msg                 pacote resultante

    Envia um ACK(seq) para o servidor.
    Por algum motivo, o servidor sempre responde com 
    b"ERROR|msg=tipo_desconhecido_ACK" então...
    """

    pacote = msg.Ack(seq)
    return send_recv(clientSocket, pacote)

def fin(clientSocket: socket, checksum: str) -> msg.Done|msg.Timeout|msg.Error:
    """
        clientSocket:socket socket
        checksum:str        Checksum para enviar ao servidor
    ->  str                 Integridade do arquivo

    Envia FIN ao servidor, e já retorna o valor da resposta DONE
    do servidor. Tenta restransmissões de acordo com cfg.maxRetries,
    se falhar nisso retornará False
    """

    pacote = msg.Fin(checksum)
    return send_recv(clientSocket, pacote)

def ping(clientSocket: socket) -> msg.Pong|msg.Timeout|msg.Error:
    """
        clientSocket:socket socket
        checksum:str        Checksum para enviar ao servidor
    ->  str                 Integridade do arquivo

    Envia FIN ao servidor, e já retorna o valor da resposta DONE
    do servidor. Tenta restransmissões de acordo com cfg.maxRetries,
    se falhar nisso retornará False
    """

    pacote = msg.Ping()
    return send_recv(clientSocket, pacote)