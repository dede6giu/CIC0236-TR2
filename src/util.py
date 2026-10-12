import configurations as cfg
import hashlib
from math import floor
from time import time

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
        filePath += str(int(time()))
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
                blocksOnBar: int = 25) -> None:
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
    endchar = "\n" if current == total else ""
    
    print(loadbar, end=endchar)