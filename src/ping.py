import configurations as cfg
import clientserver as cs
import util
import time
import mensagens as msg

def send_recv(clientSocket: socket) -> msg.Pong|msg.Timeout|msg.Error:
    pacote = msg.Ping()
    rtrnMsg, rawdata, RTT = cs.send_pick_header(clientSocket, pacote)
    if rtrnMsg == "PONG":
        return msg.Pong(RTT, rawdata)
    elif rtrnMsg == "TIMEOUT":
        return msg.Timeout("Servidor não respondeu")
    elif rtrnMsg == "ERROR":
        return msg.Error(RTT, rawdata)
    return msg.Error(-1, b"Erro desconhecido")

def ping(clientSocket: socket) -> None:
    """
        clientSocket:socket socket
    
    Envia um PING ao servidor
    """
    print("=-"*cfg.hl)
    print("Enviando PING...")

    # Envia pacote PING
    srvResponse = send_recv(clientSocket)
    
    if isinstance(srvResponse, msg.Pong):
        print("PONG!")
        print(f"RTT: {srvResponse.RTT*1000}ms")
        print(f"Server Timestamp: {srvResponse.pretty_time()}")
    elif isinstance(srvResponse, msg.Timeout):
        print(f"TIMEOUT: {srvResponse.msg}")
    elif isinstance(srvResponse, msg.Error):
        print(f"ERRO: {srvResponse.msg}")
    else:
        print(f"Retorno desconhecido do servidor: {rawdata}")
    return