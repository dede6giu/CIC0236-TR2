# Programa config
hl = 30 ## Tamanho console bar

# Server info
serverName = '137.131.178.229'
serverPort = 8080
server = (serverName, serverPort)
pcksize = 2048 ## recvfrom()
encoding = 'utf-8'

# Configs Genéricas
baseTimeout = 5.0
grupo = 'grupo03'
filetype = 'small' ## small / medium / large
filePathBase = './results/'
seqSizeDefault = 1024
reqWindowSizeDefault = 4
loseRate = 0

# CSV Column Constants
csvSEGMENT = (0, int, "segment")
csvTIMESTAMP = (1, str, "timestamp")
csvSIZEBYTES = (2, int, "sizebytes")
csvRTT = (3, float, "rtt")
csvEST = (4, float, "rttest")
csvTIMEOUTMS = (5, float, "timeoutms")
csvTHROUGHPUT = (6, float, "throughput")
csvRETRANSMISSIONS = (7, int, "retransmissions")
csvTIMEOUTHAPPENED = (8, int, "timeoutoccurred")
csvWINDOWSIZE = (9, int, "windowsize")
csvPROTOCOL = (10, str, "protocol")