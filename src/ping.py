import configurations as cfg
import clientserver as cs
from util import get_meta_until as process_message
from time import strftime, gmtime

def ping() -> None:
    """
    Envia um PING ao servidor
    """
    print("=-"*cfg.hl)
    print("Enviando PING...")

    # Envia pacote PING
    packet = "PING"
    try:
        rawdata, RTT = cs.send_message(packet)
    except socket.timeout:
        print("Erro: SERVER TIMEOUT")
        return
    
    # Processa retorno
    rtrnMsg, data = process_message(rawdata)
    if rtrnMsg == b'PONG':    
        print("PONG!")
        print(f"RTT: {RTT*1000}ms")
        print(f"Server Timestamp: {strftime("%a, %d %b %Y %H:%M:%S", gmtime(float(data["time"])))}")
    elif rtrnMsg == b'ERROR':
        print(f'Erro: {data["msg"]}')
    else:
        print(f'Retorno desconhecido do servidor: {rawdata}')
    return