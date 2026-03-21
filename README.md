# ⛏ EduChain — Blockchain Central em Python

Blockchain completa baseada em Ethereum com mineração automática, servidor RPC e token EDU.

## 🚀 Como usar

### Opção 1 — Iniciar tudo junto (recomendado)
```bash
python main.py
```
Isso inicia o RPC Server + Interface do minerador em conjunto.

### Opção 2 — Separado (2 terminais)
```bash
# Terminal 1 — Servidor RPC
python rpc_server.py

# Terminal 2 — Interface do minerador
python miner.py
```

## 📋 Fluxo

1. Programa inicia
2. **Eduardo digita o endereço da carteira** (ou gera um automaticamente)
3. Mineração começa automaticamente
4. Blocos são minerados com Proof of Work (dificuldade 4)
5. Recompensa em EDU vai direto para a carteira
6. Dashboard atualiza em tempo real

## 🔗 API RPC (Ethereum-compatible)

### Endpoints GET
```
GET /chain          → dados da blockchain
GET /balance/{addr} → saldo de um endereço
GET /stats          → estatísticas de mineração
```

### Endpoints POST (JSON-RPC)
```json
{"method": "eth_getBalance",    "params": ["0x..."]}
{"method": "eth_blockNumber"}
{"method": "eth_sendTransaction","params": [{"from":"0x...","to":"0x...","value":10}]}
{"method": "miner_start",       "params": ["0x..."]}
{"method": "miner_stop"}
{"method": "miner_stats"}
```

## 💡 Características

| Recurso | Detalhe |
|---|---|
| Token | EDU (EduChain) |
| Algoritmo | SHA-256 Proof of Work |
| Dificuldade | 4 zeros iniciais |
| Recompensa inicial | 50 EDU / bloco |
| Halving | A cada 100 blocos |
| RPC Port | 8545 (padrão Ethereum) |

## 📁 Arquivos

```
educhain/
├── main.py         ← Lançador principal (use este)
├── blockchain.py   ← Core da blockchain e bloco
├── rpc_server.py   ← Servidor RPC HTTP
├── miner.py        ← Interface terminal do minerador
└── README.md
```
