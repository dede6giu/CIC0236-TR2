import configurations as cfg
import clientserver as cs
import util
from enum import Enum

class ReqResult(Enum):
    SUCCESS = 0
    N_SEG = 1
    N_SIZE = 4
    TIMEOUT = 2
    ERROR = 3

def send_handshake(clientSocket: socket) -> ReqResult:
    """
        clientSocket:socket     socket para o handshake
    ->  ReqResult               sucesso/fracasso da operação

    Realiza o handshake e transforma em um resultado legíve
    para o módulo.
    """

    handshakeSuccess = cs.handshake(clientSocket)
    if handshakeSuccess == "OK":
        return ReqResult.SUCCESS
    if handshakeSuccess == "TIMEOUT":
        return ReqResult.TIMEOUT
    return ReqResult.ERRO

def send_req(clientSocket: socket, seq: int) -> (ReqResult, str|bytes):
    """
        clientSocket:socket     conexão (já com handshake)
        seq:int                 número de sequência
    ->  (ReqResult, str|bytes)  (resultado, msg|payload)

    Requisita a sequência seq para o servidor e já retorna o payload
    em caso de sucesso.
    """

    pacote = f'REQ|seq={seq}'
    rtrnMsg, rawdata, RTT = cs.send_pick_header(pacote, clientSocket)

    if rtrnMsg == 'ERROR':
        data = util.get_meta_until(rawdata)
        return (ReqResult.ERROR, data["msg"])
    if rtrnMsg == 'TIMEOUT':
        data = util.get_meta_until(rawdata)
        return (ReqResult.TIMEOUT, data["msg"])
    if rtrnMsg != 'DATA':
        return (ReqResult.ERROR, "Mensagem desconhecida do servidor")

    data = util.get_meta_until(rawdata, 2)
    if seq != int(data["seq"]):
        return (ReqResult.N_SEG, "Segmento incorreto.")
    # if len(data["payload"]) != int(data["total"]):
    #     print(f"{len(data["payload"])} != {int(data["total"])}")
    #     return (ReqResult.N_SIZE, "Tamanho incorreto.")
    
    return (ReqResult.SUCCESS, data["payload"])

def send_ack(clientSocket: socket, seq: int) -> ReqResult:
    """
        clientSocket:socket     conexão (já com handshake)
        seq:int                 número de sequência
    ->  ReqResult               sucesso/fracasso da operação

    Envia um ACK(seq) para o servidor.
    """

    pacote = f"ACK|seq={seq}"
    rtrnMsg, rawdata, RTT = cs.send_pick_header(pacote, clientSocket)
    return (rtrnMsg, rawdata)

def saw(clientSocket: socket, filePath: str) -> ReqResult:
    """
        clientSocket:socket     conexão (já com handshake)
        filePath:str            onde salvar o arquivo
    ->  ReqResult               sucesso/fracasso da operação

    Executa o protocolo Stop-and-Wait para baixar um arquivo.
    """

    # Execução
    seqCurrent = 0
    while (seqCurrent < cfg.seqTotalAmount):
        # Enviar REQ
        attempts = 0
        while attempts < cfg.maxRetries:
            # print(f"REQ {seqCurrent}: Tentativa {attempts+1}...")
            resultType, reqData = send_req(clientSocket, seqCurrent)
            if resultType == ReqResult.SUCCESS:
                send_ack(clientSocket, seqCurrent)
                break
            attempts += 1
        # print(resultType)
        
        # Manejamento de erros
        if resultType == ReqResult.ERROR:
            print(f"ERRO: {reqData["msg"]}")
            continue # para tentar receber novamente
        elif resultType == ReqResult.TIMEOUT:
            return ReqResult.TIMEOUT
        elif resultType == ReqResult.N_SEG:
            print(f"ERRO: Número de segmento incorreto.")
            continue # para tentar receber novamente
        elif resultType != ReqResult.SUCCESS:
            print(f"ERRO: Erro desconhecido")
            continue # para tentar receber novamente
            
        # Sucesso: Salvar resultado
        with open(filePath, "ab") as f:
            f.write(reqData)
        seqCurrent += 1
        util.print_loadbar(seqCurrent, cfg.seqTotalAmount)

    return ReqResult.SUCCESS

def main() -> None:
    """
    Embrulha o método Stop And Wait em uma função. 
    """

    clientSocket = cs.make_socket()

    # Realizar handshake
    aux = send_handshake(clientSocket)
    if aux == ReqResult.ERROR:
        print("ERRO: Handshake falhou")
        clientSocket.close()
        return
    if aux == ReqResult.TIMEOUT:
        print("TIMEOUT: Servidor não respondeu ao handshake")
        clientSocket.close()
        return

    # Caminho para o arquivo...
    filePath = ''
    if cfg.filetype == 'small':
        filePath = cfg.pathsml
    elif cfg.filetype == 'medium':
        filePath = cfg.pathmed
    elif cfg.filetype == 'big':
        filePath = cfg.pathbig
    with open(filePath, "wb+"):
        pass # Esvazia o arquivo

    # Stop-And-Wait
    resultOperation = saw(clientSocket, filePath)
    if resultOperation == ReqResult.TIMEOUT:
        print(f"TIMEOUT: O servidor não respondeu depois de {cfg.maxRetries} tentativas")
        clientSocket.close()
        return
    elif resultOperation == ReqResult.ERROR:
        print(f"ERRO: Algum erro aconteceu")
        return
    elif resultOperation != ReqResult.SUCCESS:
        print(f"ERRO: Resultado desconhecido")
        return

    # Verificação do arquivo
    if cfg.checksum != util.do_md5(filePath):
        print(f"ERRO: Checksum diferente, tente rebaixar")
        return

    # SUCESSO
    print(f"SUCESSO: Arquivo '{cfg.filetype}' baixado.")

    return