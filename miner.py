import os
import sys
import time
import json
import threading
import hashlib
import random
import urllib.request
import urllib.error

RPC_URL = "http://127.0.0.1:8545"
REFRESH = 1.5


def rpc(method, params=None):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or [], "id": 1}).encode()
    req = urllib.request.Request(RPC_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def get_chain():
    req = urllib.request.Request(f"{RPC_URL}/chain", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read())
    except:
        return {}


def get_balance(address):
    req = urllib.request.Request(f"{RPC_URL}/balance/{address}", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read()).get("balance", 0)
    except:
        return 0


def generate_address(name="eduardo"):
    seed = f"{name}-{random.randint(1000,9999)}"
    return "0x" + hashlib.sha256(seed.encode()).hexdigest()[:40]


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def bar(value, max_val=100, width=20, char="█", empty="░"):
    filled = int((value / max(max_val, 1)) * width)
    return char * filled + empty * (width - filled)


def format_hash(h: str) -> str:
    return h[:8] + "..." + h[-6:] if h and len(h) > 16 else h


def dashboard(address: str):
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    frame = 0
    start_time = time.time()

    while True:
        try:
            stats_resp = rpc("miner_stats")
            stats = stats_resp.get("result", {})
            chain = get_chain()
            balance = get_balance(address)

            clear()
            uptime = int(time.time() - start_time)
            h, m, s = uptime // 3600, (uptime % 3600) // 60, uptime % 60

            spin = frames[frame % len(frames)]
            frame += 1

            mining = stats.get("is_mining", False)
            blocks = stats.get("blocks_mined", 0)
            earned = stats.get("total_earned", 0.0)
            hashrate = stats.get("hash_rate", 0)
            chain_len = chain.get("length", 0)
            reward = chain.get("block_reward", 50)
            supply = chain.get("total_supply", 0)
            pending = chain.get("pending_transactions", 0)

            status_icon = f"🟢 {spin} MINERANDO" if mining else "🔴 PARADO"

            print("╔══════════════════════════════════════════════════════════════╗")
            print("║          ⛏  EDUCHAIN MINER  —  EDU Token  v1.0             ║")
            print("╠══════════════════════════════════════════════════════════════╣")
            print(f"║  Status : {status_icon:<52}║")
            print(f"║  Uptime : {h:02d}:{m:02d}:{s:02d}    Chain: #{chain_len:<6}  Pending txs: {pending:<8}║")
            print("╠══════════════════════════════════════════════════════════════╣")
            print(f"║  🏦  Endereço : {address[:20]}...{address[-6:]}         ║")
            print(f"║  💰  Saldo    : {balance:>12.4f} EDU                              ║")
            print(f"║  🏆  Blocos   : {blocks:>8}     Ganho total: {earned:>10.4f} EDU    ║")
            print(f"║  ⚡  Hash/s   : {hashrate:>10,}   Recompensa : {reward:>10.2f} EDU    ║")
            print("╠══════════════════════════════════════════════════════════════╣")

            # Progresso visual
            hr_bar = bar(min(hashrate, 500000), 500000, 30)
            print(f"║  Hash Rate  [{hr_bar}] {hashrate:,}/s      ║")
            bal_bar = bar(min(balance, 1000), 1000, 30)
            print(f"║  Saldo EDU  [{bal_bar}] {balance:.2f} EDU    ║")

            print("╠══════════════════════════════════════════════════════════════╣")

            # Últimos blocos
            recent_blocks = chain.get("blocks", [])[-4:]
            if recent_blocks:
                print("║  📦 Blocos recentes:                                         ║")
                for b in reversed(recent_blocks):
                    idx = b.get("index", 0)
                    miner = b.get("miner", "?")
                    rew = b.get("reward", 0)
                    bh = format_hash(b.get("hash", ""))
                    is_me = "✅" if miner == address else "  "
                    print(f"║  {is_me} #{idx:<5} | {bh:<16} | +{rew:.1f} EDU              ║")

            print("╠══════════════════════════════════════════════════════════════╣")
            print("║  [Q] Sair   [S] Stop   [R] Reiniciar mineração               ║")
            print("╚══════════════════════════════════════════════════════════════╝")
            print(f"\n  Supply total: {supply:.4f} EDU  |  Dificuldade: {chain.get('difficulty', 4)} zeros  |  Rede válida: {'✅' if chain.get('is_valid') else '❌'}")

        except KeyboardInterrupt:
            print("\n\n👋 Saindo do EduChain Miner...")
            rpc("miner_stop")
            sys.exit(0)
        except Exception as e:
            print(f"\n  ⚠ Erro de conexão: {e}")

        time.sleep(REFRESH)


def main():
    clear()
    print("╔══════════════════════════════════════════════════════╗")
    print("║          ⛏  EDUCHAIN — Configuração inicial         ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    print("  Insira o endereço da carteira de Eduardo para receber EDU.")
    print("  (Deixe em branco para gerar automaticamente)\n")

    addr_input = input("  Endereço (0x...): ").strip()

    if not addr_input:
        addr_input = generate_address("eduardo")
        print(f"\n  ✅ Endereço gerado: {addr_input}")

    address = addr_input
    print(f"\n  Iniciando mineração para: {address}")
    print("  Conectando ao RPC Server...")
    time.sleep(1)

    result = rpc("miner_start", [address])
    if "error" in result:
        print(f"\n  ❌ Erro: {result['error']}")
        print("  Certifique-se que o RPC server está rodando: python rpc_server.py")
        sys.exit(1)

    print("  ✅ Mineração iniciada!\n")
    time.sleep(0.5)
    dashboard(address)


if __name__ == "__main__":
    main()
