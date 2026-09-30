def get_meta_until(raw: bytes, n: int = -1) -> (bytes, {str, str|bytes}):
    """
        raw:bytes   raw byte data
        n:int       qtd de headers, padrão -1. negativo implica que a msg inteira é header
    ->  (bytes, {str, str|bytes})   (message type, {header key, header value})

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
    
    rtrnMsg = auxres[0]
    auxres.pop(0)

    # Quebrar headers em key->value
    lastbytes = 1 if n >= 0 else 0
    for i in range(len(auxres)-lastbytes):
        kv = (auxres[i].decode()).split('=')
        result[kv[0]] = kv[1]
    # Se o último campo for data, salvar como bytes
    if lastbytes == 1:
        result["payload"] = auxres[-1]

    return (rtrnMsg, result)