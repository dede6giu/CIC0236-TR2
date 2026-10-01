import configurations as cfg

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
        return ('ERROR', 'msg=Mensagem incompreensivel do servidor'.encode(cfg.encoding))

def get_meta_until(raw: bytes, n: int = -1) -> {str, str|bytes}:
    """
        raw:bytes           raw byte data
        n:int               qtd headers, padrão -1. negativo == msg inteira é header
    ->  {str, str|bytes}    {header key, header value}

    Espera-se que raw seja do formato:
        b'key1=value1|key2=value2|...|keyN=valueN|payload'
    """
    result = {}
    auxres = []

    # Adquirir headers
    pos = 0
    amt = 0
    firstloop = 0
    while pos > -1:
        aux = raw.find(b'|', pos+firstloop)
        if aux == -1 or amt == n:
            auxres.append(raw[pos+firstloop:])
            break
        else:
            auxres.append(raw[pos+firstloop:aux])
            pos = aux
            amt += 1
        firstloop = 1

    # Quebrar headers em key->value
    lastbytes = 1 if n >= 0 else 0
    for i in range(len(auxres)-lastbytes):
        kv = (auxres[i].decode()).split('=')
        result[kv[0]] = kv[1]
    # Se o último campo for data, salvar como bytes
    if lastbytes == 1:
        result["payload"] = auxres[-1]

    return result