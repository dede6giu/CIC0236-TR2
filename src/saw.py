import configurations as cfg
import clientserver as cs

def main():
    if cs.handshake():
        print(f"handshake sucesso! prova: {cfg.checksum}")
    else:
        print("handshake falhou!")
    pass