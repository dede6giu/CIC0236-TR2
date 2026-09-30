import socket
import time

def hexedBytes(data: bytes) -> str:
  return " ".join(f"{b:02x}" for b in data)

def getMetaUntil(raw: bytes, n:int = -1) -> {str, str|bytes}:
  """
  MUST be used after getting the command return type.
  Expects raw to be bytes and of the format:
    b'key1=value1|key2=value2|...|keyn=valuen|payload'
  """
  result = {}
  auxres = []

  # Gather metadata camps
  pos = 0
  amt = 0
  firstloop = 0
  while pos > -1:
    aux = raw.find(b'|', pos+1)
    if aux == -1 or amt == n:
      auxres.append(raw[pos+firstloop:])
      break
    else:
      auxres.append(raw[pos+firstloop:aux])
    pos = aux
    amt += 1
    firstloop = 1

  # Split metadata into key->value
  lastbytes = 1 if n >= 0 else 0
  for i in range(len(auxres)-lastbytes):
    kv = (auxres[i].decode()).split('=')
    result[kv[0]] = kv[1]
  if lastbytes == 1:
    result["payload"] = auxres[-1]

  return result





if __name__ == "__main__":
  # Server info
  serverName = '137.131.178.229'
  serverPort = 8080
  encod = 'utf-8'

  # Client setup
  clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  clientSocket.settimeout(5.0)

  print("=== Tarefa 0 - RDT-UnB Explorer ===")
  print(f"Servidor: {serverName}:{serverPort}")
  print()

  # Message loop
  while True:
    print("=-"*30)
    message = (input('Input: ')).strip().upper()

    # Message adjustment
    clientpackt = {}
    pacote = message
    if message == 'QUIT' or message == 'Q':
      break
    elif message == 'HELLO':
      clientpackt["grupo"] = "grupo03"
      clientpackt["segsize"] = "512"
      clientpackt["filesize"] = "small"
      pacote = f'HELLO|grupo={clientpackt["grupo"]}|segment_size={clientpackt["segsize"]}|file={clientpackt["filesize"]}'
    elif message == 'REQ':
      clientpackt["segval"] = (input('Input valor seq: ')).strip()
      pacote = f'REQ|seq={clientpackt["segval"]}'

    # Sending message
    print()
    timeStart = time.time()
    clientSocket.sendto(pacote.encode(encod), (serverName, serverPort))
    try:
      data, server = clientSocket.recvfrom(2048)
      timeEnd = time.time()
      rawdata = data
    except socket.timeout:
      rawdata = b'TIMEDOUT'

    # Obtaining response type
    if rawdata != b'TIMEOUT':
      firstbar = rawdata.find(b'|')
      if firstbar != -1:
        returntype = rawdata[0:firstbar].decode()
        data = rawdata[firstbar+1:]
      else:
        returntype = 'UNKNOWN'
    else:
      returntype = 'TIMEDOUT'

    # Parsing answer
    if returntype == 'PONG':
      retpact = getMetaUntil(data)
      timeServer = float(retpact["time"])
      print("PING")
      print(f'machine->server: {(timeServer-timeStart)*1000}ms')
      print(f'server->machine: {(timeEnd-timeServer)*1000}ms')
      print(f'RTT:             {(timeEnd-timeStart)*1000}ms')

    elif returntype == 'OK':
      retpact = getMetaUntil(data)
      print("HELLO")
      print(f'Arquivo:        {clientpackt["filesize"]} ({int(retpact["file_size"])} bytes = {int(retpact["file_size"])//1024} KB)')
      print(f'Checksum MD5:   {retpact["checksum"]}')
      print(f'Qtd. segmentos: {retpact["total_segments"]}')
      print(f'Tmn. segmento:  {retpact["segment_size"]}')

    elif returntype == 'DATA':
      retpact = getMetaUntil(data, 2)
      f8b = hexedBytes(retpact["payload"])[:26]
      print(f'REQ seg={clientpackt["segval"]}')
      print(f'Payload recebido: {retpact["total"]} bytes')
      print(f'Primeiros 8 bytes: {f8b}')

    elif returntype == 'ERROR':
      retpact = getMetaUntil(data)
      print(f'Erro do servidor: {retpact["msg"]}')

    elif returntype == 'TIMEDOUT':
      print('Servidor não respondeu a tempo.')

    else:
      # Unknown server reply
      print(f'Resposta desconhecida: {hexedBytes(rawdata)}')
