# Programa config
hl = 30 ## Tamanho console bar

# Server info
serverName = '137.131.178.229'
serverPort = 8080
server = (serverName, serverPort)
pcksize = 65536 ## recvfrom()
encoding = 'utf-8'

# Configs Genéricas
baseTimeout = 5.0
grupo = 'grupo03'
filetype = 'small' ## small / medium / large
filePathBase = './results/'
seqSizeDefault = 512
reqWindowSizeDefault = 4
loseRate = 0

# RTT Adaptativo
rttAdapativo = False
rttAlpha = 0.125
rttBeta = 0.25
rttEst = 0
rttDev = 0
rttTimeout = 0

# CSV Column Constants
csvSEGMENT = (0, int, "segment")
csvTIMESTAMP = (1, str, "timestamp")
csvUNIX = (2, float, "time_unix")
csvSIZEBYTES = (3, int, "sizebytes")
csvRTT = (4, float, "rtt")
csvEST = (5, float, "rttest")
csvTIMEOUTMS = (6, float, "timeoutms")
csvTHROUGHPUT = (7, float, "throughput")
csvRETRANSMISSIONS = (8, int, "retransmissions")
csvTIMEOUTHAPPENED = (9, int, "timeoutoccurred")
csvWINDOWSIZE = (10, int, "windowsize")
csvPROTOCOL = (11, str, "protocol")
csvLOSS = (12, float, "simulated_loss")
