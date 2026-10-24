import configurations as cfg
import clientserver as cs
import util
import time
import graphs
import mensagens as msg
from threading import Thread
from queue import Empty, Queue

def csvQueue(queue: Queue) -> None:
    curr = 0
    while True:
        try:
            item = queue.get()
        except Empty:
            continue
        else:
            if item[1] != curr:
                queue.task_done()
                queue.put(item)
                continue
            curr += 1
            util.do_csv(*item)
            queue.task_done()

def fileQueue(queue: Queue, filePath: str) -> None:
    curr = 0
    while True:
        try:
            item = queue.get()
        except Empty:
            continue
        else:
            if item.seq != curr:
                queue.task_done()
                queue.put(item)
                continue
            curr += 1
            with open(filePath, "ab") as f:
                f.write(item.payload)
            queue.task_done()

def sr(clientSocket, hsOk, filePath):

    # CSV Setup
    csvProtocol = "sr"
    csvFileName = f"metrics_{cfg.grupo}_{csvProtocol}_"
    csvFileName += time.strftime(f"%Y%m%d_%H%M%S", time.gmtime(time.time() - time.timezone))
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
    payloadReceived = set()

    seqCurrent = 0
    while (seqCurrent < hsOk.totalSegments):
        # Vars para a barra
        loadbarTime = time.time()
        totalSegSize = 0

        # Enviar windowSize REQs
        currWindow = min(windowSize, hsOk.totalSegments-seqCurrent)
        reqThreadQueue = Queue()
        for i in range(currWindow):
            treatSeq = seqCurrent+i
            if treatSeq in payloadReceived:
                continue # já tem o seq
            aux = util.ThreadRet(
                target=lambda sock, seq : cs.req(sock, seq),
                args=(clientSocket, treatSeq,)
            )
            aux.start()
            if hadTimeout.get(treatSeq) == None:
                hadTimeout[treatSeq] = False
            if amountRetransmissions.get(treatSeq) == None:
                amountRetransmissions[treatSeq] = 0
            reqThreadQueue.put(aux)
        
        # Receber DATA arbitrariamente
        while not reqThreadQueue.empty():
            srvResponse = (reqThreadQueue.get()).join()
            treatSeq = srvResponse.seq

            # Timeout / Erro
            if treatSeq < 0:
                continue
            if isinstance(srvResponse, msg.Timeout):
                hadTimeout[treatSeq] = True
                amountRetransmissions[treatSeq] = amountRetransmissions[treatSeq]+1
                continue
            if isinstance(srvResponse, msg.Error):
                amountRetransmissions[treatSeq] = amountRetransmissions[treatSeq]+1
                continue
            
            # Sucesso!
            payloadReceived.add(treatSeq)
            
            # CSV data
            csvTimestamp = time.time()
            csvSizeBytes = len(srvResponse.payload)
            csvRTT = srvResponse.RTT
            csvRTTEst = srvResponse.RTT
            csvTimeout = clientSocket.gettimeout()
            csvThroughput = (csvSizeBytes) / (1000*csvRTT)
            csvRetransmissions = amountRetransmissions[treatSeq]
            csvTimeoutHappened = hadTimeout[treatSeq]
            csvWindowSize = currWindow
            csvPending.put((
                csvFileName,
                treatSeq,
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
            totalSegSize += csvSizeBytes
            
            # Salvar resultado
            filePending.put(srvResponse)
        
        while seqCurrent in payloadReceived:
            seqCurrent += 1

        # Visualização da barra de carregamento
        util.print_loadbar(
            seqCurrent, 
            hsOk.totalSegments,
            throughput=totalSegSize/(1000*(time.time()-loadbarTime))
        )
    filePending.join()
    csvPending.join()
    return csvFileName


def main(clientSocket: socket) -> None:
    """
    Embrulha o método Selective Repeat em uma função. 
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
    csvFileName = sr(clientSocket, handshakeResult, filePath)

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