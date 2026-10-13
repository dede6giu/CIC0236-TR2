import configurations as cfg
import clientserver as cs
import mensagens as msg
import util
import time
import graphs

def saw(clientSocket: socket, hsOk: msg.Ok, filePath: str) -> str:
    """
        clientSocket:socket     conexão (já com handshake)
        hsOk:msg.Ok             dados da conexão (handshakeOk)
        filePath:str            onde salvar o arquivo
    ->  str                     nome do resultado em csv

    Executa o protocolo Stop-and-Wait para baixar um arquivo.
    """

    seqCurrent = 0
    csvTimestamp = time.time()
    csvFileName = f"metrics_{cfg.grupo}_saw_"
    csvFileName += time.strftime(f"%Y%m%d_%H%M%S", time.gmtime(csvTimestamp - time.timezone))
    csvRetransmissions = 0
    csvTimeoutHappened = False
    while (seqCurrent < hsOk.totalSegments):
        # Enviar REQ
        srvResponse = cs.req(clientSocket, seqCurrent)
        if not isinstance(srvResponse, msg.Data):
            # Manejamento de erros
            if csvRetransmissions == 0 and seqCurrent != 0: print()
            if isinstance(srvResponse, msg.Error):
                print(f"ERRO: {srvResponse.msg}")
            elif isinstance(srvResponse, msg.Timeout):
                print(f"TIMEOUT: Servidor não respondeu ao REQ({seqCurrent})")
                csvTimeoutHappened = True
            elif not isinstance(srvResponse, msg.Data):
                print(f"ERRO: Erro desconhecido")
            csvRetransmissions += 1
            continue # para tentar receber novamente

        # Sucesso!

        # CSV data
        csvTimestamp = time.time()
        csvSizeBytes = len(srvResponse.payload)
        csvRTT = srvResponse.RTT
        csvRTTEst = srvResponse.RTT
        csvTimeout = clientSocket.gettimeout()
        csvThroughput = csvSizeBytes / (1000*csvRTT)
        csvWindowSize = 1
        csvProtocol = "saw"
        util.do_csv(
            csvFileName,
            seqCurrent,
            csvTimestamp,
            csvSizeBytes,
            csvRTT,
            csvRTTEst,
            csvTimeout,
            csvThroughput,
            csvRetransmissions,
            csvTimeoutHappened,
            csvWindowSize,
            csvProtocol
        )

        # Salvar resultado
        with open(filePath, "ab") as f:
            f.write(srvResponse.payload)
        seqCurrent += 1

        # ACK
        cs.ack(clientSocket, seqCurrent)

        # Visualização da barra de carregamento
        util.print_loadbar(seqCurrent, hsOk.totalSegments)

        # Reset das variáveis
        csvRetransmissions = 0
        csvTimeoutHappened = False

    return csvFileName

def main(clientSocket: socket) -> None:
    """
    Embrulha o método Stop And Wait em uma função. 
    """

    # Definir timeout
    clientSocket.settimeout(cfg.baseTimeout)

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
    csvFileName = saw(clientSocket, handshakeResult, filePath)

    # Verificação do arquivo
    receivedChecksum = util.do_md5(filePath)
    fileStatus = cs.fin(clientSocket, receivedChecksum)
    while not isinstance(fileStatus, msg.Done):
        fileStatus = cs.fin(clientSocket, receivedChecksum)
        print(fileStatus)
    if not fileStatus.ok:
        print(f"FALHA: Checksum de '{cfg.filetype}' não correspondeu")
        return

    print(f"SUCESSO: Arquivo '{cfg.filetype}' baixado e verificado")
    opcao = input(f"Deseja ver os gráficos de throughput e RTT? [y/N]: ")
    showGraphs = True if opcao.upper() == "Y" else False
    graphs.singleColumnLine(csvFileName, cfg.csvTHROUGHPUT, showGraphs=showGraphs)
    graphs.singleColumnLine(csvFileName, cfg.csvRTT, showGraphs=showGraphs)
    return