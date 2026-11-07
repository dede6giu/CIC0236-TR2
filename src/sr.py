import configurations as cfg
import clientserver as cs
import util
import time
import graphs
import mensagens as msg
from threading import Thread
from queue import Empty, Queue
import random as rand

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
            if item < 0:
                queue.task_done()
                continue
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
    rttPending.put(hsOk.RTT)

    # Estado inicial das variáveis
    currTimeout = cfg.baseTimeout
    windowSize = cfg.reqWindowSizeDefault
    seqCurrent = 0
    seqNext = 0
    packetReceived = dict()
    reqList = dict()
    amountSent = dict()
    hadTimeout = dict()
    simulatedLoss = dict()

    for i in range(hsOk.totalSegments):
        packetReceived[i] = False
        reqList[i] = -1
        amountSent[i] = 0
        hadTimeout[i] = False
        simulatedLoss[i] = 0

    # Protocolo SR
    while seqCurrent < hsOk.totalSegments:
        if cfg.rttAdapativo:
            currTimeout = cfg.rttTimeout
            clientSocket.settimeout(currTimeout)

        currWindow = seqCurrent + min(windowSize, hsOk.totalSegments-seqCurrent)
        while seqNext < currWindow:
            reqList[seqNext] = cs.just_send(clientSocket, msg.Req(seqNext))[0]
            amountSent[seqNext] += 1
            seqNext += 1
        seqTransit = [seq for seq in range(seqCurrent, seqNext) if not packetReceived[seq]]

        # time.sleep(0.012)

        timeMax = time.time() + currTimeout
        rcvData = cs.get_all_packets(clientSocket, len(seqTransit))

        for p in rcvData:
            srvResponse = cs.mount_data(p[0], reqList, p[1])
            seqTreat = srvResponse.seq
            if seqTreat < 0 or packetReceived[seqTreat]:
                continue
            if seqTransit.count(seqTreat) == 0:
                continue
            if seqTreat < seqCurrent or seqTreat > seqNext:
                continue
            seqRTT = srvResponse.RTT

            # Erro / Timeout
            if isinstance(srvResponse, msg.Error):
                if not srvResponse.clientSide:
                    rttPending.put(seqRTT)
                continue
            if isinstance(srvResponse, msg.Timeout):
                hadTimeout[seqTreat] = True
                break
            if not isinstance(srvResponse, msg.Data):
                continue

            # Simulação de perda
            if rand.random() < cfg.loseRate:
                rttPending.put(seqRTT)
                simulatedLoss[seqTreat] += 1
                continue

            # Sucesso!
            rttPending.put(seqRTT)
            cs.ack(clientSocket, seqTreat)
            packetReceived[seqTreat] = True
            seqTransit.remove(seqTreat)
            filePending.put(srvResponse)

            # CSV data
            csvTimestamp = time.time()
            csvSizeBytes = cfg.seqSizeDefault
            csvRTT = seqRTT
            csvRTTEst = cfg.rttEst
            csvTimeout = currTimeout
            csvThroughput = (csvSizeBytes) / (1000*csvRTT)
            csvRetransmissions = amountSent[seqTreat]-1
            csvTimeoutHappened = hadTimeout[seqTreat]
            csvWindowSize = cfg.reqWindowSizeDefault
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

        for seqTreat in seqTransit:
            reqList[seqTreat] = cs.just_send(clientSocket, msg.Req(seqTreat))[0]
            amountSent[seqTreat] += 1

        while packetReceived.get(seqCurrent):
            seqCurrent += 1
        
        # Barra de carregamento
        util.print_loadbar(
            seqCurrent, 
            hsOk.totalSegments,
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