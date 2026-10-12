import configurations as cfg
import clientserver as cs
import mensagens as msg
import util
from enum import Enum

class ReqResult(Enum):
    SUCCESS = 0
    N_SEG = 1
    N_SIZE = 4
    TIMEOUT = 2
    ERROR = 3

def send_ack(clientSocket: socket, seq: int) -> ReqResult:
    """
        clientSocket:socket     conexão (já com handshake)
        seq:int                 número de sequência
    ->  ReqResult               sucesso/fracasso da operação

    Envia um ACK(seq) para o servidor.
    """

    pacote = f"ACK|seq={seq}"
    rtrnMsg, rawdata, RTT = cs.send_pick_header(clientSocket, pacote)
    return (rtrnMsg, rawdata)

def saw(clientSocket: socket, hsOk: msg.Ok, filePath: str) -> None:
    """
        clientSocket:socket     conexão (já com handshake)
        hsOk:msg.Ok             dados da conexão (handshakeOk)
        filePath:str            onde salvar o arquivo

    Executa o protocolo Stop-and-Wait para baixar um arquivo.
    """

    seqCurrent = 0
    while (seqCurrent < hsOk.totalSegments):
        # Enviar REQ
        hasFailed = False
        srvResponse = cs.req(clientSocket, seqCurrent)
        if not isinstance(srvResponse, msg.Data):
            # Manejamento de erros
            if not hasFailed: print()
            if isinstance(srvResponse, msg.Error):
                print(f"ERRO: {srvResponse.msg}")
            elif isinstance(srvResponse, msg.Timeout):
                print(f"TIMEOUT: Servidor não respondeu ao REQ({seqCurrent})")
            elif not isinstance(srvResponse, msg.Data):
                print(f"ERRO: Erro desconhecido")
            hasFailed = True
            continue # para tentar receber novamente
        hasFailed = False

        # Sucesso!
        # ACK
        cs.ack(clientSocket, seqCurrent)

        # Salvar resultado
        with open(filePath, "ab") as f:
            f.write(srvResponse.payload)
        seqCurrent += 1

        # Visualização da barra de carregamento
        util.print_loadbar(seqCurrent, hsOk.totalSegments)

    return

def main(clientSocket: socket) -> None:
    """
    Embrulha o método Stop And Wait em uma função. 
    """

    # Realizar handshake
    handshakeResult = cs.handshake(clientSocket)

    if isinstance(handshakeResult, msg.Error):
        print("ERRO: Handshake falhou")
        return
    if isinstance(handshakeResult, msg.Timeout):
        print("TIMEOUT: Servidor não respondeu ao handshake")
        return

    # Caminho para o arquivo...
    filePath = util.get_file_path(handshakeResult)
    with open(filePath, "wb+"):
        pass # Esvazia o arquivo

    # Stop-And-Wait
    saw(clientSocket, handshakeResult, filePath)
    
    # Verificação do arquivo
    receivedChecksum = util.do_md5(filePath)
    fileStatus = cs.fin(clientSocket, receivedChecksum)
    while not isinstance(fileStatus, msg.Done):
        fileStatus = cs.fin(clientSocket, receivedChecksum)
        print(fileStatus)
    if fileStatus.ok:
        print(f"SUCESSO: Arquivo '{cfg.filetype}' baixado e verificado")
    else:
        print(f"FALHA: Checksum de '{cfg.filetype}' não correspondeu")
    return