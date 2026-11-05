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
            if item[1] > curr:
                queue.task_done()
                queue.put(item)
                continue
            if item[1] < curr:
                queue.task_done()
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
            if item.seq > curr:
                queue.task_done()
                queue.put(item)
                continue
            if item.seq < curr:
                queue.task_done()
                continue
            curr += 1
            with open(filePath, "ab") as f:
                f.write(item.payload)
            queue.task_done()

def rttQueue(queue: Queue) -> None:
    while True:
        try:
            item = queue.get()
        except Empty:
            continue
        else:
            cfg.rttEst = (1-cfg.rttAlpha) * cfg.rttEst 
            cfg.rttEst += cfg.rttAlpha * item
            
            cfg.rttDev = (1-cfg.rttBeta) * cfg.rttDev
            cfg.rttDev += cfg.rttBeta * abs(item - cfg.rttEst)

            cfg.rttTimeout = cfg.rttEst + 4*cfg.rttDev
            queue.task_done()

def gbn(clientSocket, hsOk, filePath):
    # CSV Setup
    csvProtocol = "gbn"
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
    firstSentAt = dict()
    simulatedLoss = dict()

    cfg.rttEst = hsOk.RTT
    cfg.rttDev = 0
    cfg.rttTimeout = cfg.baseTimeout
    rttPending = Queue()
    rttThread = Thread(
        target=rttQueue,
        args=(rttPending,),
        daemon=True
    )
    rttThread.start()

    seqCurrent = 0
    while (seqCurrent < hsOk.totalSegments):
        # Ajustar timeout
        if cfg.rttAdapativo:
            clientSocket.settimeout(cfg.rttTimeout)

        # Vars para a barra
        loadbarTime = time.time()
        totalSegSize = 0

        # Enviar windowSize REQs
        currWindow = min(windowSize, hsOk.totalSegments-seqCurrent)
        reqThreadQueue = Queue()
        for i in range(currWindow):
            treatSeq = seqCurrent+i
            aux = util.ThreadRet(
                target=lambda sock, seq : cs.req(sock, seq),
                args=(clientSocket, treatSeq,),
                daemon=True
            )
            aux.start()
            if hadTimeout.get(treatSeq) == None:
                hadTimeout[treatSeq] = False
            if simulatedLoss.get(treatSeq) == None:
                simulatedLoss[treatSeq] = 0
            if amountRetransmissions.get(treatSeq) == None:
                amountRetransmissions[treatSeq] = 0
            if firstSentAt.get(treatSeq) == None:
                firstSentAt[treatSeq] = time.time()
            reqThreadQueue.put(aux)

        # Receber DATA em ordem
        i = 0
        while i < currWindow:
            srvResponse = (reqThreadQueue.get(block=False)).join()
            i += 1
            treatSeq = srvResponse.seq
            # seqRTT = srvResponse.RTT
            seqRTT = time.time() - firstSentAt[treatSeq]

            # Timeout / Erro
            if treatSeq < 0:
                continue
            if isinstance(srvResponse, msg.Timeout):
                hadTimeout[treatSeq] = True
                amountRetransmissions[treatSeq] = amountRetransmissions[treatSeq]+1
                rttPending.put(clientSocket.gettimeout())
                continue
            if isinstance(srvResponse, msg.Error):
                amountRetransmissions[treatSeq] = amountRetransmissions[treatSeq]+1
                if not srvResponse.clientSide:
                    rttPending.put(seqRTT)
                if srvResponse.msg == "Pacote descartado pelo cliente":
                    simulatedLoss[treatSeq] += 1
                continue

            # Número de seq incorreto, joga fora
            if treatSeq != seqCurrent:
                amountRetransmissions[treatSeq] = amountRetransmissions[treatSeq]+1
                rttPending.put(seqRTT)
                continue

            # Sucesso!
            rttPending.put(seqRTT)
            cs.ack(clientSocket, treatSeq)
            
            # CSV data
            csvTimestamp = time.time()
            csvSizeBytes = cfg.seqSizeDefault
            csvRTT = seqRTT
            csvRTTEst = cfg.rttEst
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
                csvProtocol,
                simulatedLoss[treatSeq]
            ))
            totalSegSize += csvSizeBytes
            
            # Salvar resultado
            filePending.put(srvResponse)
            
            # Atualizar valor de seqCurrent
            seqCurrent += 1

        # Visualização da barra de carregamento
        util.print_loadbar(
            seqCurrent, 
            hsOk.totalSegments,
            throughput=totalSegSize/(1000*(time.time()-loadbarTime))
        )
    filePending.join()
    csvPending.join()
    rttPending.join()
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
    if not fileStatus.ok:
        print(f"FALHA: Checksum de '{cfg.filetype}' não correspondeu")
        return

    print(f"SUCESSO: Arquivo '{cfg.filetype}' baixado e verificado")
    opcao = input(f"Deseja ver os gráficos de throughput e RTT? [y/N]: ")
    showGraphs = True if opcao.upper() == "Y" else False
    graphs.singleColumnLine(csvFileName, cfg.csvTHROUGHPUT, showGraphs=showGraphs)
    graphs.singleColumnLine(csvFileName, cfg.csvRTT, showGraphs=showGraphs)
    return