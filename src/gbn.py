import configurations as cfg
import clientserver as cs
import util
import time
import graphs
import mensagens as msg
from threading import Thread
from queue import Empty, Queue

def csvQueue(queue: Queue) -> None:
    while True:
        try:
            item = queue.get()
        except Empty:
            continue
        else:
            util.do_csv(*item)
            queue.task_done()

def fileQueue(queue: Queue, filePath: str) -> None:
    while True:
        try:
            item = queue.get()
        except Empty:
            continue
        else:
            with open(filePath, "ab") as f:
                f.write(item)
            queue.task_done()

# def reqThread(clientSocket, seq):
#     return cs.req(clientSocket, seq)

def gbn(clientSocket, hsOk, filePath):

    # CSV Setup
    csvTimestampPrevious = time.time()
    csvProtocol = "gbn"
    csvFileName = f"metrics_{cfg.grupo}_{csvProtocol}_"
    csvFileName += time.strftime(f"%Y%m%d_%H%M%S", time.gmtime(csvTimestampPrevious - time.timezone))
    csvRetransmissions = 0
    csvTimeoutHappened = False
    csvPending = Queue()
    csvThread = Thread(
        target=csvQueue,
        args=(csvPending,),
        daemon=True
    )
    csvThread.start()

    # Outros setup
    filePending = Queue()
    fileThread = Thread(
        target=fileQueue,
        args=(filePending, filePath,),
        daemon=True
    )
    fileThread.start()
    windowSize = cfg.reqWindowSizeDefault
    amountRetransmissions = dict()
    hadTimeout = dict()

    csvTimestampPrevious = time.time()
    seqCurrent = 0
    while (seqCurrent < hsOk.totalSegments):
        # Enviar windowSize REQs
        currWindow = min(windowSize, hsOk.totalSegments-seqCurrent)
        reqThreadQueue = Queue()
        for i in range(currWindow):
            aux = util.ThreadRet(
                target=lambda sock, seq : cs.req(sock, seq),
                args=(clientSocket, seqCurrent+i,)
            )
            aux.start()
            reqThreadQueue.put(aux)
        
        
        # Receber DATA em ordem
        totalSegSize = 0
        anyTimedout = False
        while not reqThreadQueue.empty():
            srvResponse = (reqThreadQueue.get()).join()
            # Timeout / Erro
            if isinstance(srvResponse, msg.Timeout):
                anyTimedout = True
                hadTimeout[treatSeq] = True
                amountRetransmissions[treatSeq] = amountRetransmissions[treatSeq]+1
                continue
            if isinstance(srvResponse, msg.Error):
                amountRetransmissions[treatSeq] = amountRetransmissions[treatSeq]+1
                continue

            treatSeq = str(srvResponse.seq)
            if amountRetransmissions.get(treatSeq) == None:
                amountRetransmissions[treatSeq] = 0
            
            # Se outra seq timeout, retransmita
            if anyTimedout:
                amountRetransmissions[treatSeq] = amountRetransmissions[treatSeq]+1
                continue

            # Número de seq incorreto, pula
            if srvResponse.seq != seqCurrent:
                amountRetransmissions[treatSeq] = amountRetransmissions[treatSeq]+1
                continue

            # Sucesso!
            
            # CSV data
            csvTimestamp = time.time()
            csvSizeBytes = len(srvResponse.payload)
            csvRTT = srvResponse.RTT
            csvRTTEst = srvResponse.RTT
            csvTimeout = clientSocket.gettimeout()
            csvThroughput = (csvSizeBytes) / (1000*(csvTimestamp-csvTimestampPrevious))
            csvWindowSize = currWindow
            csvPending.put((
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
            ))
            
            # Salvar resultado
            filePending.put(srvResponse.payload)
            
            # Atualizar valor de seqCurrent
            cs.ack(clientSocket, seqCurrent)
            seqCurrent += 1

        # Visualização da barra de carregamento
        util.print_loadbar(
            seqCurrent, 
            hsOk.totalSegments, 
            throughput=(csvSizeBytes) / (1000*(csvTimestamp-csvTimestampPrevious))
        )

        # reset variáveis
        csvTimestampPrevious = csvTimestamp
    return csvFileName


def main(clientSocket: socket) -> None:
    """
    Embrulha o método Go-Back-N em uma função. 
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
    csvFileName = gbn(clientSocket, handshakeResult, filePath)

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