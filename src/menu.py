import configurations as cfg
import ping
import time

def main_menu() -> None:
    print("=-"*cfg.hl)
    print("Trabalho TR2 - Grupo 03")
    while True:
        print("=-"*cfg.hl)
        print("Menu Principal\n")
        print("0. PING")
        print("1. Testar SAW")
        print("2. Testar GBN")
        print("3. Testar SR")
        print("4. Testar RTT Adaptativo")
        print("7. Ver perguntas")
        print("8. Alterar configurações")
        print("9. Sair do programa")
        
        print("=-"*cfg.hl)
        opcao = input("Escolha uma opção: ")
        try:
            opcao = int(opcao)
        except:
            print("Opção inválida")
            continue

        match opcao:
            case 0:
                ping.ping()
            case 1|2|3|4|7|8:
                print("Não implementado!")
            case 9:
                break
            case _:
                print("Opção inválida")
        
        time.sleep(1.2)