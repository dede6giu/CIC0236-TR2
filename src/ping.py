import configurations as cfg
import clientserver as cs
import util
from time import strftime, gmtime

def ping() -> None:
    """
    Envia um PING ao servidor
    """
    print("=-"*cfg.hl)
    print("Enviando PING...")

    # Envia pacote PING
    packet = "PING"
    rtrnMsg, rawdata, RTT = cs.send_pick_header(packet)
    data = util.get_meta_until(rawdata)
    if rtrnMsg == 'PONG':    
        print("PONG!")
        print(f"RTT: {RTT*1000}ms")
        print(f"Server Timestamp: {strftime("%a, %d %b %Y %H:%M:%S", gmtime(float(data["time"])))}")
    elif rtrnMsg == 'ERROR':
        print(f'Erro: {data["msg"]}')
    else:
        print(f'Retorno desconhecido do servidor: {rawdata}')
    return