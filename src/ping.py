import configurations as cfg
import clientserver as cs
import util
import time

def ping(clientSocket: socket) -> None:
    """
    Envia um PING ao servidor
    """
    print("=-"*cfg.hl)
    print("Enviando PING...")

    # Envia pacote PING
    packet = "PING"
    rtrnMsg, rawdata, RTT = cs.send_pick_header(clientSocket, packet)
    data = util.get_meta_until(rawdata)
    if rtrnMsg == 'PONG':    
        print("PONG!")
        print(f"RTT: {RTT*1000}ms")
        serverTime = time.gmtime(float(data["time"]) - time.timezone)
        print(f"Server Timestamp: {time.strftime(f"%a, %d %b %Y %H:%M:%S UTC{time.tzname[0]}", serverTime)}")
    elif rtrnMsg == 'ERROR':
        print(f'Erro: {data["msg"]}')
    elif rtrnMsg == 'TIMEOUT':
        print(f'Timeout: {data["msg"]}')
    else:
        print(f'Retorno desconhecido do servidor: {rawdata}')
    return