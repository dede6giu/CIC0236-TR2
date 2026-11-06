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
    cfg.rttEst = 0
    cfg.rttDev = 0
    cfg.rttTimeout = cfg.baseTimeout
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

    # File buffering / building
    filePending = Queue()
    fileThread = Thread(
        target=fileQueue,
        args=(filePending, filePath,),
        daemon=True
    )
    fileThread.start()

    # Cálculo do RTT dinâmico
    rttPending = Queue()
    rttThread = Thread(
        target=rttQueue,
        args=(rttPending,),
        daemon=True
    )
    rttThread.start()
    rttPending.put(hsOk.RTT)

    # Estado inicial das variáveis
    windowSize = cfg.reqWindowSizeDefault
    seqCurrent = 0
    currTimeout = cfg.baseTimeout
    packetReceived = set()

    amountSent = dict()
    simulatedLoss = dict()
    hadTimeout = dict()
    for i in range(hsOk.totalSegments):
        if hadTimeout.get(i) == None:
            hadTimeout[i] = False
        if simulatedLoss.get(i) == None:
            simulatedLoss[i] = 0
        if amountSent.get(i) == None:
            amountSent[i] = 0

    # Protocolo SR
    while seqCurrent < hsOk.totalSegments:
        # Reset de variáveis
        if cfg.rttAdapativo:
            currTimeout = cfg.rttTimeout
        seqAux = 0
        timeStart = 0
        reqList = list()
        currWindow = min(windowSize, hsOk.totalSegments-seqCurrent)
        totalSegSize = 0
        loadbarTime = time.time()

        # Envia a janela de REQs
        while seqAux < currWindow:
            seqTreat = seqCurrent + seqAux
            if seqTreat in packetReceived:
                seqAux += 1
                continue
            reqList.append(cs.just_send(clientSocket, msg.Req(seqTreat)))
            amountSent[seqTreat] += 1
            seqAux += 1
        
        timeStart = reqList[0][0]
        reqAmount = len(reqList)
        i = 0
        while i < reqAmount and time.perf_counter()-timeStart <= currTimeout:
            srvResponse = cs.just_recv(clientSocket, *reqList[i])
            seqTreat = srvResponse.seq
            seqRTT = srvResponse.RTT

            # Erro
            if isinstance(srvResponse, msg.Error):
                if not srvResponse.clientSide:
                    rttPending.put(seqRTT)
                if srvResponse.msg == "Pacote descartado pelo cliente":
                    simulatedLoss[seqTreat] += 1
                i += 1
                continue

            # Sucesso!
            rttPending.put(seqRTT)
            packetReceived.add(seqTreat)
            
            # CSV data
            csvTimestamp = time.perf_counter()
            csvSizeBytes = cfg.seqSizeDefault
            csvRTT = seqRTT
            csvRTTEst = cfg.rttEst
            csvTimeout = currTimeout
            csvThroughput = (csvSizeBytes) / (1000*csvRTT)
            csvRetransmissions = amountSent[seqTreat]-1
            csvTimeoutHappened = hadTimeout[seqTreat]
            csvWindowSize = currWindow
            csvSimulatedLoss = simulatedLoss[seqTreat]
            csvPending.put((
                csvFileName,
                seqTreat,
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
                csvSimulatedLoss
            ))
            totalSegSize += csvSizeBytes
            
            # Salvar resultado
            filePending.put(srvResponse)
            
            i += 1

        # Timeout!
        while i < reqAmount:
            srvResponse = cs.just_recv(clientSocket, *reqList[i])
            hadTimeout[srvResponse.seq] = True
            i += 1

        # Atualizar seqCurrent
        while seqCurrent in packetReceived:
            cs.ack(clientSocket, seqCurrent)
            seqCurrent += 1

        # Barra de carregamento
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
    Embrulha o método Selective-Repeat em uma função. 
    """

    # Definir timeout
    clientSocket.settimeout(cfg.baseTimeout)

    # Realizar handshake
    handshakeResult = cs.handshake(clientSocket)
    while not isinstance(handshakeResult, msg.Ok):
        if isinstance(handshakeResult, msg.Error):
            print("ERRO: Handshake falhou")
        if isinstance(handshakeResult, msg.Timeout):
            print("TIMEOUT: Servidor não respondeu ao handshake")
        handshakeResult = cs.handshake(clientSocket)


    # Caminho para o arquivo...
    filePath = util.get_file_path(handshakeResult)
    with open(filePath, "wb+"):
        pass # Esvazia o arquivo

    # Selective-repeat
    csvFileName = sr(clientSocket, handshakeResult, filePath)

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