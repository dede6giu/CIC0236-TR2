import time

class Pacote:
    def __init__(self, header: str, RTT: float):
        self.header = header
        self.RTT = RTT
        self.clientSide = self.RTT < 0

    def __str__(self):
        return self.stringify()

    def stringify(self):
        return self.header

    def get_meta_until(self, raw: bytes, n: int = -1) -> {str, str|bytes}:
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


class Error(Pacote):
    def __init__(self, RTT: float, rawdata: bytes):
        Pacote.__init__(self, "ERROR", RTT)
        if self.clientSide:
            self.msg = rawdata.decode()
        else:
            self.msg = self.get_meta_until(rawdata)["msg"]
    
    def stringify(self):
        return self.header + f"|msg={self.msg}"

class Timeout(Pacote):
    def __init__(self, msg: str):
        Pacote.__init__(self, "TIMEOUT", -1)
        self.msg = msg

class Ping(Pacote):
    def __init__(self):
        Pacote.__init__(self, "PING", -1)

class Pong(Pacote):
    def __init__(self, RTT: float, rawdata: bytes):
        Pacote.__init__(self, "PONG", RTT)
        self.timestamp = float(self.get_meta_until(rawdata)["time"])

    def stringify(self):
        return self.header + f"|time={self.timestamp}"

    def pretty_time(self):
        serverTime = time.gmtime(self.timestamp - time.timezone)
        return time.strftime(f"%a, %d %b %Y %H:%M:%S UTC{time.tzname[0]}", serverTime)