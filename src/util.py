import configurations as cfg
import hashlib
from math import floor
import time
import csv

def get_return_type(raw: bytes) -> (str, bytes):
    """
        raw:bytes       raw byte data
    ->  (str, bytes)    (message header, resto da mensagem)
    
    Extrai apenas o tipo do retorno da mensagem.
    Retorna ('ERROR', b'msg=Mensagem incompreensível do servidor') em erro.
    """
    firstbar = raw.find(b'|')
    if firstbar != -1:
        returntype = raw[0:firstbar].decode(cfg.encoding)
        data = raw[firstbar+1:]
        return (returntype, data)
    else:
        return ('ERROR', b'msg=Mensagem incompreensivel do servidor')

def get_file_path(hsOk: msg.Ok):
    filePath = cfg.filePathBase
    if hsOk == None:
        filePath += str(int(time.time()))
        return filePath
    filePath += str(hsOk.seed)
    filePath += f"_({cfg.filetype})"
    return filePath

def do_md5(filePath: str) -> str:
    """
        filePath:str    caminho do arquivo
    ->  str             MD5 resultante
    
    Calcula o MD5 do arquivo filePath.
    """

    with open(filePath, "rb") as f:
        content = f.read()
    return (hashlib.md5(content)).hexdigest()

def print_loadbar(current: int, total: int, *, 
                charFilled: str = '█', charEmpty: str = ' ',
                phraseBefore: str = 'Baixando: ',
                charLeft: str = '「', charRight: str = '」',
                doNumCount: bool = True,
                blocksOnBar: int = 25,
                throughput: float = 0, throughputRate: int = 16,
                end: str = "\n") -> None:
    """
    Cria uma barra de carregamento.
    """
    
    percent = (current / total)
    fill = int(percent * blocksOnBar)
    empty = blocksOnBar - fill
    
    loadbar = '\r'
    loadbar += phraseBefore
    loadbar += charLeft
    loadbar += charFilled * fill
    loadbar += charEmpty * empty
    loadbar += charRight
    if doNumCount:
        loadbar += f" {current}/{total} "
    else:
        loadbar += " "
    loadbar += f"({int(percent*100)}%)"
    if throughput > 0 and current % throughputRate == 0:
        loadbar += f" {throughput:.2f}kB/s"
    endchar = end if current == total else ""
    
    print(loadbar, end=endchar)

def do_csv(
        fileName: str,
        segment: int,
        timestamp: float,
        sizeBytes: int,
        rtt: float,
        rttEst: float,
        timeoutMS: float,
        throughput: float,
        retransmission: int,
        timeoutHappened: bool,
        windowSize: int,
        protocol: str
        ) -> None:
    fields = ["segment", "timestamp", "size_bytes", "rtt_ms",
    "rtt_estimated_ms", "timeout_ms", "throughput_kbps", "retransmissions",
    "timeout_occurred", "window_size", "protocol"]
    filePath = cfg.filePathBase + fileName + ".csv"
    timestamp = time.strftime(f"%Y-%m-%dT%H:%M:%S", time.gmtime(timestamp))
    row = []
    row.append(str(segment))
    row.append(str(timestamp))
    row.append(str(sizeBytes))
    row.append(str(rtt*1000))
    row.append(str(rttEst*1000))
    row.append(str(timeoutMS*1000))
    row.append(str(throughput))
    row.append(str(retransmission))
    row.append(str(1 if timeoutHappened else 0))
    row.append(str(windowSize))
    row.append(str(protocol))
    try:
        f = open(filePath, "x")
        f.close()
        with open(filePath, "w") as csvFile:
            csvWriter = csv.writer(csvFile)
            csvWriter.writerow(fields)
    except FileExistsError:
        pass
    with open(filePath, "a") as csvFile:
        csvWriter = csv.writer(csvFile)
        csvWriter.writerow(row)
    return

def list_from_csv_column(fileName, column) -> list:
    filePath = cfg.filePathBase + fileName + ".csv"
    with open(filePath, "r") as csvFile:
        csvReader = csv.reader(csvFile)
        result = []
        isHeader = True
        for row in csvReader:
            if isHeader:
                isHeader = False
                continue
            result.append(row[column])
    return result
            