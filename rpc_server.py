"""
EduChain RPC Server — Compatível com MetaMask / Ethereum JSON-RPC
Chain ID: 13337
RPC Port: 8545
Página web: http://127.0.0.1:8545/
"""

import json
import time
import threading
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from blockchain import EduChain

# ─── Configurações da rede ─────────────────────────────────────────────────────
CHAIN_ID        = 13337
CHAIN_ID_HEX    = hex(CHAIN_ID)       # "0x3419"
NETWORK_VERSION = str(CHAIN_ID)
GAS_PRICE_WEI   = 1_000_000_000       # 1 Gwei
GAS_LIMIT        = 21_000
WEI_PER_EDU     = 10 ** 18            # 1 EDU = 1e18 wei

# ─── Estado global ─────────────────────────────────────────────────────────────
blockchain      = EduChain()
_mining_thread  = None
_mining_active  = False
_miner_address  = ""
_tx_pool: dict  = {}
_mining_stats   = {
    "blocks_mined": 0, "total_earned": 0.0,
    "hash_rate": 0, "last_block_time": None, "is_mining": False,
}

# ─── Helpers ───────────────────────────────────────────────────────────────────

def to_wei(edu: float) -> int:
    return int(edu * WEI_PER_EDU)

def from_wei(val) -> float:
    if isinstance(val, str):
        val = int(val, 16) if val.startswith("0x") else int(val)
    return val / WEI_PER_EDU

def hex_to_int(h) -> int:
    if isinstance(h, int): return h
    return int(h, 16) if isinstance(h, str) and h.startswith("0x") else int(h)

def norm(addr: str) -> str:
    return addr.lower() if addr and addr.startswith("0x") else addr or ""

def block_to_eth(block, full_txs=False) -> dict:
    txs = []
    for i, tx in enumerate(block.transactions):
        raw_hash = tx.get("tx_hash", hashlib.sha256(str(tx).encode()).hexdigest())
        tx_hash  = raw_hash if raw_hash.startswith("0x") else "0x" + raw_hash
        if full_txs:
            txs.append({
                "hash": tx_hash, "nonce": hex(i),
                "blockHash": "0x" + block.hash, "blockNumber": hex(block.index),
                "transactionIndex": hex(i),
                "from": norm(tx.get("sender", "0x0")),
                "to":   norm(tx.get("recipient", "0x0")),
                "value": hex(to_wei(tx.get("amount", 0))),
                "gas": hex(GAS_LIMIT), "gasPrice": hex(GAS_PRICE_WEI), "input": "0x",
                "v": "0x1", "r": "0x" + "0"*64, "s": "0x" + "0"*64,
            })
        else:
            txs.append(tx_hash)
    return {
        "number": hex(block.index), "hash": "0x" + block.hash,
        "parentHash": "0x" + block.previous_hash,
        "nonce": hex(block.nonce),
        "sha3Uncles": "0x" + "0"*64, "logsBloom": "0x" + "0"*512,
        "transactionsRoot": "0x" + "0"*64, "stateRoot": "0x" + "0"*64,
        "receiptsRoot": "0x" + "0"*64,
        "miner": norm(block.miner) if block.miner else "0x0",
        "difficulty": hex(blockchain.DIFFICULTY),
        "totalDifficulty": hex(blockchain.DIFFICULTY * max(block.index, 1)),
        "extraData": "0x", "size": hex(1000),
        "gasLimit": hex(8_000_000),
        "gasUsed": hex(GAS_LIMIT * len(block.transactions)),
        "timestamp": hex(int(block.timestamp)),
        "transactions": txs, "uncles": [],
    }

# ─── Mineração automática ──────────────────────────────────────────────────────

def _auto_mine():
    global _mining_stats
    while _mining_active:
        if _miner_address:
            t0    = time.time()
            block = blockchain.mine_block(_miner_address)
            elapsed = time.time() - t0
            _mining_stats["blocks_mined"]   += 1
            _mining_stats["total_earned"]   += block.reward
            _mining_stats["hash_rate"]       = int(block.nonce / max(elapsed, 0.001))
            _mining_stats["last_block_time"] = time.time()
            for i, tx in enumerate(block.transactions):
                h = tx.get("tx_hash", "")
                if not h.startswith("0x"): h = "0x" + h
                _tx_pool[h] = {
                    "transactionHash": h,
                    "transactionIndex": hex(i),
                    "blockHash": "0x" + block.hash,
                    "blockNumber": hex(block.index),
                    "from": norm(tx.get("sender", "0x0")),
                    "to":   norm(tx.get("recipient", "0x0")),
                    "cumulativeGasUsed": hex(GAS_LIMIT),
                    "gasUsed": hex(GAS_LIMIT),
                    "contractAddress": None, "logs": [],
                    "logsBloom": "0x" + "0"*512, "status": "0x1",
                }
        time.sleep(0.5)

# ─── Handler HTTP ──────────────────────────────────────────────────────────────

class MetaMaskRPCHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args): pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/metamask"):
            self._html(METAMASK_PAGE)
        elif path == "/chain":
            self._json(blockchain.get_chain_data())
        elif path == "/stats":
            self._json({**_mining_stats, "is_mining": _mining_active})
        elif path.startswith("/balance/"):
            addr = path.split("/balance/")[1]
            bal  = blockchain.get_balance(addr)
            self._json({"address": addr, "balance": bal, "balance_wei": to_wei(bal), "symbol": "EDU"})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            data = json.loads(body) if body else {}
        except Exception:
            self._json({"error": "invalid JSON"}, 400); return
        if isinstance(data, list):
            self._json([self._rpc(r) for r in data])
        else:
            self._json(self._rpc(data))

    def ok(self, result, rid):
        return {"jsonrpc": "2.0", "result": result, "id": rid}

    def err(self, code, msg, rid):
        return {"jsonrpc": "2.0", "error": {"code": code, "message": msg}, "id": rid}

    def _rpc(self, data: dict) -> dict:
        m  = data.get("method", "")
        p  = data.get("params", [])
        id = data.get("id")

        # ── Identidade ─────────────────────────────────────────────────────────
        if   m == "eth_chainId":             return self.ok(CHAIN_ID_HEX, id)
        elif m == "net_version":             return self.ok(NETWORK_VERSION, id)
        elif m == "net_listening":           return self.ok(True, id)
        elif m == "net_peerCount":           return self.ok("0x1", id)
        elif m == "eth_protocolVersion":     return self.ok("0x41", id)
        elif m == "web3_clientVersion":      return self.ok("EduChain/v1.0/python", id)
        elif m == "eth_syncing":             return self.ok(False, id)
        elif m == "web3_sha3":
            raw = bytes.fromhex(p[0][2:]) if p and p[0].startswith("0x") else (p[0] or "").encode()
            return self.ok("0x" + hashlib.sha3_256(raw).hexdigest(), id)

        # ── Blocos ─────────────────────────────────────────────────────────────
        elif m == "eth_blockNumber":
            return self.ok(hex(len(blockchain.chain) - 1), id)

        elif m == "eth_getBlockByNumber":
            tag  = p[0] if p else "latest"
            full = p[1] if len(p) > 1 else False
            if tag in ("latest", "pending"): blk = blockchain.last_block
            elif tag == "earliest":          blk = blockchain.chain[0]
            else:
                idx = hex_to_int(tag)
                blk = blockchain.chain[idx] if idx < len(blockchain.chain) else None
            return self.ok(block_to_eth(blk, full) if blk else None, id)

        elif m == "eth_getBlockByHash":
            h    = (p[0] or "").replace("0x", "")
            full = p[1] if len(p) > 1 else False
            blk  = next((b for b in blockchain.chain if b.hash == h), None)
            return self.ok(block_to_eth(blk, full) if blk else None, id)

        elif m == "eth_getBlockTransactionCountByNumber":
            tag = p[0] if p else "latest"
            blk = blockchain.last_block if tag in ("latest","pending") else \
                  (blockchain.chain[hex_to_int(tag)] if hex_to_int(tag) < len(blockchain.chain) else None)
            return self.ok(hex(len(blk.transactions) if blk else 0), id)

        elif m in ("eth_getUncleCountByBlockNumber","eth_getUncleCountByBlockHash"):
            return self.ok("0x0", id)

        # ── Contas / Saldo ─────────────────────────────────────────────────────
        elif m == "eth_accounts":
            return self.ok(list(blockchain.balances.keys())[:5], id)

        elif m == "eth_getBalance":
            addr = norm(p[0] if p else "")
            return self.ok(hex(to_wei(blockchain.get_balance(addr))), id)

        elif m == "eth_getTransactionCount":
            addr = norm(p[0] if p else "")
            nonce = sum(1 for b in blockchain.chain for tx in b.transactions
                        if norm(tx.get("sender","")) == addr)
            return self.ok(hex(nonce), id)

        # ── Gas ────────────────────────────────────────────────────────────────
        elif m == "eth_gasPrice":            return self.ok(hex(GAS_PRICE_WEI), id)
        elif m == "eth_estimateGas":         return self.ok(hex(GAS_LIMIT), id)
        elif m == "eth_maxPriorityFeePerGas":return self.ok(hex(GAS_PRICE_WEI), id)
        elif m == "eth_feeHistory":
            n = hex_to_int(p[0]) if p else 1
            return self.ok({
                "oldestBlock": hex(max(0, len(blockchain.chain)-n)),
                "baseFeePerGas": [hex(GAS_PRICE_WEI)]*(n+1),
                "gasUsedRatio": [0.5]*n,
                "reward": [[hex(GAS_PRICE_WEI)]]*n,
            }, id)

        # ── Transações ─────────────────────────────────────────────────────────
        elif m == "eth_sendTransaction":
            tp     = p[0] if p else {}
            sender = norm(tp.get("from",""))
            recip  = norm(tp.get("to",""))
            amount = from_wei(tp.get("value","0x0"))
            tx = blockchain.add_transaction(sender, recip, amount)
            if tx:
                return self.ok("0x" + tx.tx_hash, id)
            return self.err(-32000, "Saldo insuficiente", id)

        elif m == "eth_sendRawTransaction":
            raw = p[0] if p else "0x"
            tx_hash = "0x" + hashlib.sha256(raw.encode()).hexdigest()
            return self.ok(tx_hash, id)

        elif m == "eth_getTransactionByHash":
            h = p[0] if p else ""
            r = _tx_pool.get(h)
            if r:
                return self.ok({
                    "hash": h, "nonce": "0x0",
                    "blockHash": r["blockHash"], "blockNumber": r["blockNumber"],
                    "transactionIndex": r["transactionIndex"],
                    "from": r["from"], "to": r["to"],
                    "value": "0x0", "gas": hex(GAS_LIMIT),
                    "gasPrice": hex(GAS_PRICE_WEI), "input": "0x",
                }, id)
            return self.ok(None, id)

        elif m == "eth_getTransactionReceipt":
            return self.ok(_tx_pool.get(p[0] if p else ""), id)

        elif m == "eth_getTransactionByBlockNumberAndIndex":
            return self.ok(None, id)

        # ── Código / Storage ───────────────────────────────────────────────────
        elif m == "eth_getCode":             return self.ok("0x", id)
        elif m == "eth_getStorageAt":        return self.ok("0x"+"0"*64, id)
        elif m == "eth_call":                return self.ok("0x", id)

        # ── Logs / Filtros ─────────────────────────────────────────────────────
        elif m == "eth_getLogs":             return self.ok([], id)
        elif m == "eth_newFilter":           return self.ok("0x1", id)
        elif m == "eth_newBlockFilter":      return self.ok("0x2", id)
        elif m == "eth_newPendingTransactionFilter": return self.ok("0x3", id)
        elif m == "eth_getFilterChanges":    return self.ok([], id)
        elif m == "eth_getFilterLogs":       return self.ok([], id)
        elif m == "eth_uninstallFilter":     return self.ok(True, id)

        # ── Assinatura ─────────────────────────────────────────────────────────
        elif m in ("eth_sign","personal_sign","eth_signTypedData_v4","eth_signTypedData"):
            return self.err(-32601, "Assinatura deve ser feita pelo MetaMask", id)

        # ── Subscrições ────────────────────────────────────────────────────────
        elif m in ("eth_subscribe","eth_unsubscribe"):
            return self.ok("0x0", id)

        # ── Mineração customizada ──────────────────────────────────────────────
        elif m == "miner_start":
            global _mining_active, _mining_thread, _miner_address
            addr = norm(p[0] if p else "")
            if addr:
                _miner_address = addr
                if not _mining_active:
                    _mining_active = True
                    _mining_stats["is_mining"] = True
                    _mining_thread = threading.Thread(target=_auto_mine, daemon=True)
                    _mining_thread.start()
                return self.ok("mining_started", id)
            return self.err(-32602, "Endereço inválido", id)

        elif m == "miner_stop":
            _mining_active = False
            _mining_stats["is_mining"] = False
            return self.ok("mining_stopped", id)

        elif m == "miner_stats":
            return self.ok({**_mining_stats, "is_mining": _mining_active}, id)

        else:
            return self.err(-32601, f"Método não encontrado: {m}", id)


# ─── Página MetaMask ───────────────────────────────────────────────────────────

METAMASK_PAGE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EduChain — Conectar MetaMask</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');
:root{--bg:#09090f;--s:#0f0f1a;--b:#1a1a2e;--a:#7c3aed;--c:#06b6d4;--g:#10b981;--r:#ef4444;--t:#e2e8f0;--m:#64748b}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--t);font-family:'Syne',sans-serif;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:1.5rem;
background-image:radial-gradient(ellipse at 15% 50%,#7c3aed14,transparent 55%),radial-gradient(ellipse at 85% 20%,#06b6d414,transparent 55%)}
.wrap{max-width:560px;width:100%}
.card{background:var(--s);border:1px solid var(--b);border-radius:1.5rem;padding:2rem 2.25rem;margin-bottom:1rem;box-shadow:0 0 80px #7c3aed12}
.logo{display:flex;align-items:center;gap:.75rem;margin-bottom:1.75rem}
.icon{width:50px;height:50px;background:linear-gradient(135deg,var(--a),var(--c));border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:1.6rem}
h1{font-size:1.65rem;font-weight:800}h1 em{color:var(--c);font-style:normal}
.sub{color:var(--m);font-size:.85rem;margin-top:.2rem}
.label{font-family:'Space Mono',monospace;font-size:.65rem;color:var(--m);text-transform:uppercase;letter-spacing:.1em;margin-bottom:.6rem;margin-top:1.5rem}
.row{display:flex;justify-content:space-between;align-items:center;background:var(--bg);border:1px solid var(--b);border-radius:.75rem;padding:.8rem 1rem;margin-bottom:.4rem}
.rk{color:var(--m);font-size:.82rem}.rv{font-family:'Space Mono',monospace;font-size:.82rem;color:var(--c)}
.tag{background:#7c3aed22;color:var(--a);border-radius:.35rem;padding:.1rem .45rem;font-size:.65rem;font-family:'Space Mono',monospace;margin-left:.4rem}
.btn{width:100%;padding:.95rem;border-radius:.875rem;border:none;font-family:'Syne',sans-serif;font-size:.95rem;font-weight:700;cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:.5rem;margin-top:.75rem}
.btn-p{background:linear-gradient(135deg,var(--a),#9f5fff);color:#fff}.btn-p:hover{transform:translateY(-2px);box-shadow:0 8px 28px #7c3aed40}
.btn-p:disabled{opacity:.5;transform:none;cursor:not-allowed}
.btn-s{background:transparent;border:1px solid var(--b);color:var(--t)}.btn-s:hover{border-color:var(--c);color:var(--c)}
.bar{display:flex;align-items:center;gap:.5rem;padding:.7rem 1rem;border-radius:.75rem;font-size:.85rem;margin-top:1rem}
.bar.ok{background:#10b98112;border:1px solid #10b98128;color:var(--g)}
.bar.er{background:#ef444412;border:1px solid #ef444428;color:var(--r)}
.bar.in{background:#06b6d412;border:1px solid #06b6d428;color:var(--c)}
.bar.hi{display:none}
.dot{width:8px;height:8px;border-radius:50%;background:currentColor;flex-shrink:0;animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.bal-box{text-align:center;padding:1.5rem;background:var(--bg);border:1px solid var(--b);border-radius:1rem;margin-top:.6rem}
.bal-num{font-size:2.75rem;font-weight:800;background:linear-gradient(135deg,var(--c),var(--a));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.bal-sym{color:var(--m);font-size:.85rem;margin-top:.2rem}
.addr{font-family:'Space Mono',monospace;font-size:.72rem;word-break:break-all;color:var(--c)}
.steps{display:flex;flex-direction:column;gap:.45rem}
.step{display:flex;gap:.7rem;align-items:flex-start;padding:.7rem;border-radius:.625rem;background:var(--bg);border:1px solid var(--b);font-size:.82rem;color:var(--m)}
.sn{background:var(--b);border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:.65rem;font-family:'Space Mono',monospace;flex-shrink:0;color:var(--t)}
#wallet-sec{display:none}
</style>
</head>
<body>
<div class="wrap">
<div class="card">
  <div class="logo">
    <div class="icon">⛏</div>
    <div><h1>Edu<em>Chain</em></h1><div class="sub">Rede compatível com MetaMask &nbsp;·&nbsp; Token EDU</div></div>
  </div>

  <div class="label">⚙ Configurações da Rede</div>
  <div class="row"><span class="rk">Nome da Rede</span><span class="rv">EduChain <span class="tag">Testnet</span></span></div>
  <div class="row"><span class="rk">RPC URL</span><span class="rv">http://127.0.0.1:8545</span></div>
  <div class="row"><span class="rk">Chain ID</span><span class="rv">""" + str(CHAIN_ID) + """ (""" + CHAIN_ID_HEX + """)</span></div>
  <div class="row"><span class="rk">Símbolo</span><span class="rv">EDU</span></div>
  <div class="row"><span class="rk">Decimais</span><span class="rv">18</span></div>

  <button class="btn btn-p" id="btn-net" onclick="addNetwork()">🦊 Adicionar ao MetaMask</button>
  <button class="btn btn-s" id="btn-con" style="display:none" onclick="connectWallet()">🔗 Conectar Carteira</button>

  <div class="bar hi" id="statusbar"><div class="dot"></div><span id="statusmsg"></span></div>

  <div id="wallet-sec">
    <div class="label">👛 Carteira Conectada</div>
    <div class="row"><span class="rk">Endereço</span><span class="addr" id="addr-disp">—</span></div>
    <div class="label">💰 Saldo EDU</div>
    <div class="bal-box">
      <div class="bal-num" id="bal-num">0.0000</div>
      <div class="bal-sym">EDU — EduChain Token</div>
    </div>
  </div>
</div>

<div class="card">
  <div class="label">📋 Adicionar manualmente no MetaMask</div>
  <div class="steps">
    <div class="step"><div class="sn">1</div>MetaMask → Redes → "Adicionar rede" → "Adicionar rede manualmente"</div>
    <div class="step"><div class="sn">2</div>Nome: <strong>EduChain</strong> &nbsp;|&nbsp; RPC: <strong>http://127.0.0.1:8545</strong></div>
    <div class="step"><div class="sn">3</div>Chain ID: <strong>""" + str(CHAIN_ID) + """</strong> &nbsp;|&nbsp; Símbolo: <strong>EDU</strong> &nbsp;|&nbsp; Decimais: <strong>18</strong></div>
    <div class="step"><div class="sn">4</div>Salvar → Selecionar rede EduChain → Saldo aparece automaticamente!</div>
  </div>
</div>
</div>

<script>
const RPC='http://127.0.0.1:8545';
const CID_HEX='""" + CHAIN_ID_HEX + """';

function setStatus(msg,type){
  const b=document.getElementById('statusbar');
  b.className='bar '+type;
  document.getElementById('statusmsg').textContent=msg;
}

async function addNetwork(){
  if(!window.ethereum){setStatus('MetaMask não encontrado — instale em metamask.io','er');return}
  const btn=document.getElementById('btn-net');
  btn.disabled=true; btn.textContent='Adicionando...';
  try{
    await window.ethereum.request({method:'wallet_addEthereumChain',params:[{
      chainId:CID_HEX, chainName:'EduChain',
      nativeCurrency:{name:'EduChain Token',symbol:'EDU',decimals:18},
      rpcUrls:[RPC], blockExplorerUrls:[RPC+'/chain'],
    }]});
    setStatus('Rede EduChain adicionada com sucesso!','ok');
    document.getElementById('btn-con').style.display='flex';
    await connectWallet();
  }catch(e){
    setStatus(e.code===4902?'Use a adição manual abaixo':e.message||'Erro ao adicionar rede','er');
  }
  btn.disabled=false; btn.innerHTML='🦊 Adicionar ao MetaMask';
}

async function connectWallet(){
  if(!window.ethereum)return;
  try{
    const accounts=await window.ethereum.request({method:'eth_requestAccounts'});
    if(accounts[0]) showWallet(accounts[0]);
  }catch(e){setStatus('Conexão recusada','er')}
}

async function showWallet(addr){
  document.getElementById('addr-disp').textContent=addr;
  document.getElementById('wallet-sec').style.display='block';
  setStatus('Carregando saldo...','in');
  await refreshBal(addr);
}

async function refreshBal(addr){
  try{
    const r=await fetch(RPC+'/balance/'+addr);
    const d=await r.json();
    document.getElementById('bal-num').textContent=parseFloat(d.balance||0).toFixed(4);
    setStatus('Conectado à EduChain · Recebendo EDU automaticamente','ok');
  }catch(e){document.getElementById('bal-num').textContent='—'}
}

if(window.ethereum){
  window.ethereum.on('accountsChanged',a=>{if(a[0])showWallet(a[0])});
  window.ethereum.on('chainChanged',()=>location.reload());
}

setInterval(async()=>{
  const a=document.getElementById('addr-disp').textContent;
  if(a&&a!=='—') refreshBal(a);
},3000);
</script>
</body>
</html>"""


# ─── Start ─────────────────────────────────────────────────────────────────────

def start_rpc_server(host="0.0.0.0", port=8545):
    server = HTTPServer((host, port), MetaMaskRPCHandler)
    print(f"🔗 EduChain RPC   →  http://{host}:{port}")
    print(f"🦊 MetaMask Setup →  http://127.0.0.1:{port}/")
    print(f"   Chain ID: {CHAIN_ID}  ({CHAIN_ID_HEX})")
    server.serve_forever()


if __name__ == "__main__":
    start_rpc_server()
