import configurations as cfg
import clientserver as cs
import util
import time
import mensagens as msg

def ping(clientSocket: socket) -> None:
    """
        clientSocket:socket socket
    
    Envia um PING ao servidor
    """
    print("Enviando PING...")

    # Envia pacote PING
    srvResponse = cs.ping(clientSocket)
    
    if isinstance(srvResponse, msg.Pong):
        print("PONG!")
        print(f"RTT: {srvResponse.RTT*1000}ms")
        print(f"Server Timestamp: {srvResponse.pretty_time()}")
    elif isinstance(srvResponse, msg.Timeout):
        print(f"TIMEOUT: {srvResponse.msg}")
    elif isinstance(srvResponse, msg.Error):
        print(f"ERRO: {srvResponse.msg}")
    else:
        print("ERRO: Erro desconhecido")
    return