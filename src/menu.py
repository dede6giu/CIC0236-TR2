import time
import configurations as cfg
import clientserver as cs
from ping import ping
from saw import main as saw
from configmenu import main as configs

def main_menu() -> None:
    print("=-"*cfg.hl)
    print("Trabalho TR2 - Grupo 03")
    while True:
        print("=-"*cfg.hl)
        print("Menu Principal\n")
        print("1. PING")
        print("2. Testar SAW")
        print("3. Testar GBN")
        print("4. Testar SR")
        print("5. Testar RTT Adaptativo")
        print("8. Ver perguntas")
        print("9. Alterar configurações")
        print("0. Sair do programa")
        
        print("=-"*cfg.hl)
        opcao = input("Escolha uma opção: ")
        try:
            opcao = int(opcao)
        except ValueError:
            print("Opção inválida")
            continue

        sock = cs.make_socket()
        match opcao:
            case 1:
                ping(sock)
            case 2:
                saw(sock)
            case 9:
                configs()
            case 0:
                break
            case 2|3|4|7:
                print("Não implementado!")
            case _:
                print("Opção inválida")
        cs.close_socket(sock)
        
        time.sleep(1.2)
    return