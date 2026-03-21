"""
╔══════════════════════════════════════════════════════╗
║          ⛏  EDUCHAIN — Lançador principal           ║
╚══════════════════════════════════════════════════════╝

Inicia o RPC Server + Minerador automático em conjunto.
Eduardo digita o endereço da carteira e começa a minerar EDU.
"""

import sys
import threading
import time
import os


def start_rpc():
    """Inicia o servidor RPC em background"""
    # Adiciona o diretório ao path
    sys.path.insert(0, os.path.dirname(__file__))
    from rpc_server import start_rpc_server
    start_rpc_server(port=8545)


def main():
    print("\n")
    print("  ███████╗██████╗ ██╗   ██╗ ██████╗██╗  ██╗ █████╗ ██╗███╗   ██╗")
    print("  ██╔════╝██╔══██╗██║   ██║██╔════╝██║  ██║██╔══██╗██║████╗  ██║")
    print("  █████╗  ██║  ██║██║   ██║██║     ███████║███████║██║██╔██╗ ██║")
    print("  ██╔══╝  ██║  ██║██║   ██║██║     ██╔══██║██╔══██║██║██║╚██╗██║")
    print("  ███████╗██████╔╝╚██████╔╝╚██████╗██║  ██║██║  ██║██║██║ ╚████║")
    print("  ╚══════╝╚═════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝")
    print()
    print("           🔗 Blockchain Central  •  Token EDU  •  Python")
    print()

    # Iniciar RPC Server em thread separada
    print("  [1/3] Iniciando blockchain EduChain...")
    rpc_thread = threading.Thread(target=start_rpc, daemon=True)
    rpc_thread.start()
    time.sleep(1.5)  # aguarda servidor subir
    print("  [2/3] Servidor RPC ativo em http://127.0.0.1:8545")
    time.sleep(0.5)
    print("  [3/3] Carregando interface do minerador...\n")
    time.sleep(0.5)

    # Importar e rodar o miner
    from miner import main as miner_main
    miner_main()


if __name__ == "__main__":
    main()
