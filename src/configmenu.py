import configurations as cfg
import time

def main() -> None:
    while True:
        print("=-"*cfg.hl)
        print("Configurações\n")
        print("1. Timeout Base")
        print("2. String do Grupo")
        print("3. Tamanho do arquivo")
        print("4. Diretório dos arquivos")
        print("5. Tamanho de segmento padrão")
        print("0. Retornar ao Menu Principal")
        
        print("=-"*cfg.hl)
        opcao = input("Escolha uma opção: ")
        try:
            opcao = int(opcao)
        except ValueError:
            print("Opção inválida")
            time.sleep(1.2)
            continue

        match opcao:
            case 0:
                break
            case 1:
                timeout()
            case 2:
                grupo()
            case 3:
                tamanho()
            case 4:
                diretorio()
            case 5:
                segsize()
            case _:
                print("Opção inválida")
        
        time.sleep(1.2)
    return

def timeout() -> None:
    print(f"Timeout básico atual (s): {cfg.baseTimeout}")
    novoTimeout = input(f"Escolha um novo timeout (s): ")
    try:
        novoTimeout = float(novoTimeout)
    except ValueError:
        print("Valor inválido! Insira apenas o número.")
        return
    cfg.baseTimeout = novoTimeout
    print(f"Novo timeout base (s): {cfg.baseTimeout}")
    return

def grupo() -> None:
    print(f"Grupo atual: {cfg.grupo}")
    novoGrupo = input(f"Escolha um novo grupo: ")
    try:
        novoGrupo = str(novoGrupo)
    except ValueError:
        print("Valor inválido!")
        return
    cfg.grupo = novoGrupo
    print(f"Novo grupo: {cfg.grupo}")
    return

def tamanho() -> None:
    print(f"Tamanho do arquivo atual: {cfg.filetype}")
    print(f"1. small")
    print(f"2. medium")
    print(f"3. large")
    opcao = input("Escolha uma opção: ")
    try:
        opcao = int(opcao)
    except ValueError:
        print("Opção inválida")
        return
    match opcao:
        case 1:
            cfg.filetype = 'small'
        case 2:
            cfg.filetype = 'medium'
        case 3:
            cfg.filetype = 'large'
        case _:
            print("Opção inválida")
            return
    print(f"Novo tamanho: {cfg.filetype}")
    return

def diretorio() -> None:
    print(f"Diretório atual: {cfg.filePathBase}")
    novoDir = input(f"Escolha um novo diretório: ")
    try:
        novoDir = str(novoDir)
    except ValueError:
        print("Valor inválido!")
        return
    if novoDir[-1] != '/': novoDir += '/'
    cfg.filePathBase = novoDir
    print(f"Novo diretório: {cfg.filePathBase}")
    return

def segsize() -> None:
    print(f"Tamanho de segmento atual (bytes): {cfg.seqSizeDefault}")
    novoSegSize = input(f"Escolha um novo tamanho (bytes): ")
    try:
        novoSegSize = int(novoSegSize)
    except ValueError:
        print("Valor inválido! Insira apenas o número.")
        return
    cfg.seqSizeDefault = novoSegSize
    print(f"Novo tamanho de segmento (bytes): {cfg.seqSizeDefault}")
    return