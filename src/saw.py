import configurations as cfg
import clientserver as cs
import mensagens as msg
import util
import time
import graphs
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

def saw(clientSocket: socket, hsOk: msg.Ok, filePath: str) -> str:
    """
        clientSocket:socket     conexão (já com handshake)
        hsOk:msg.Ok             dados da conexão (handshakeOk)
        filePath:str            onde salvar o arquivo
    ->  str                     nome do resultado em csv

    Executa o protocolo Stop-and-Wait para baixar um arquivo.
    """

    # CSV Setup
    csvTimestampPrevious = time.time()
    csvProtocol = "saw"
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
    
    # File buffering / building
    filePending = Queue()
    fileThread = Thread(
        target=fileQueue,
        args=(filePending, filePath,),
        daemon=True
    )
    fileThread.start()
    simulatedLoss = dict()
    for i in range(hsOk.totalSegments):
        simulatedLoss[i] = 0

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
    currTimeout = cfg.baseTimeout

    csvTimestampPrevious = time.time()
    seqCurrent = 0
    while (seqCurrent < hsOk.totalSegments):
        # RTT Adaptativo
        if cfg.rttAdapativo:
            currTimeout = cfg.rttTimeout
            clientSocket.settimeout(currTimeout)

        # Enviar REQ
        srvResponse = cs.req(clientSocket, seqCurrent)
        timeWait = time.time()
        if not isinstance(srvResponse, msg.Data):
            # Manejamento de erros
            if csvRetransmissions == 0 and seqCurrent != 0: print()
            if isinstance(srvResponse, msg.Error):
                rttPending.put(srvResponse.RTT)
            elif isinstance(srvResponse, msg.Timeout):
                csvTimeoutHappened = True
            csvRetransmissions += 1
            continue # para tentar receber novamente

        if rand.random() < cfg.loseRate:
            rttPending.put(srvResponse.RTT)
            simulatedLoss[seqCurrent] += 1
            timeWait = currTimeout - (time.time() - timeWait)
            time.sleep(0 if timeWait < 0 else timeWait)
            continue

        # Sucesso!

        # CSV data
        csvTimestamp = time.time()
        csvSizeBytes = cfg.seqSizeDefault
        csvRTT = srvResponse.RTT
        csvRTTEst = srvResponse.RTT
        csvTimeout = currTimeout
        # csvThroughput = (csvSizeBytes) / (1000*(csvTimestamp-csvTimestampPrevious))
        csvThroughput = (csvSizeBytes) / (1000*csvRTT)
        csvWindowSize = 1
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
            csvProtocol,
            simulatedLoss[seqCurrent]
        ))

        # Salvar resultado
        filePending.put(srvResponse)
        rttPending.put(srvResponse.RTT)

        # ACK
        cs.ack(clientSocket, seqCurrent)
        seqCurrent += 1

        # Visualização da barra de carregamento
        util.print_loadbar(seqCurrent, hsOk.totalSegments, throughput=csvThroughput)

        # Reset das variáveis
        csvRetransmissions = 0
        csvTimeoutHappened = False
        csvTimestampPrevious = csvTimestamp

    filePending.join()
    csvPending.join()
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