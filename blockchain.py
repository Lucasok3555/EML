import hashlib
import json
import time
import threading
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: float
    timestamp: float = field(default_factory=time.time)
    tx_hash: str = ""

    def __post_init__(self):
        if not self.tx_hash:
            data = f"{self.sender}{self.recipient}{self.amount}{self.timestamp}"
            self.tx_hash = hashlib.sha256(data.encode()).hexdigest()

    def to_dict(self):
        return asdict(self)


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List[Dict]
    previous_hash: str
    nonce: int = 0
    miner: str = ""
    reward: float = 50.0
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "miner": self.miner,
        }
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "miner": self.miner,
            "reward": self.reward,
            "hash": self.hash,
        }


class EduChain:
    """Blockchain central baseada em Ethereum - EduChain (EDU)"""

    DIFFICULTY = 4          # zeros iniciais no hash
    BLOCK_REWARD = 50.0     # recompensa por bloco minerado
    HALVING_INTERVAL = 100  # blocos para halving
    SYMBOL = "EDU"
    NAME = "EduChain"

    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.balances: Dict[str, float] = {}
        self.lock = threading.Lock()
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = Block(
            index=0,
            timestamp=time.time(),
            transactions=[],
            previous_hash="0" * 64,
            nonce=0,
            miner="genesis",
            reward=0,
            hash="0" * 64,
        )
        self.chain.append(genesis)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    @property
    def block_reward(self) -> float:
        halvings = len(self.chain) // self.HALVING_INTERVAL
        return self.BLOCK_REWARD / (2 ** halvings)

    def get_balance(self, address: str) -> float:
        return self.balances.get(address, 0.0)

    def add_transaction(self, sender: str, recipient: str, amount: float) -> Optional[Transaction]:
        if sender != "coinbase":
            balance = self.get_balance(sender)
            if balance < amount:
                return None

        tx = Transaction(sender=sender, recipient=recipient, amount=amount)
        with self.lock:
            self.pending_transactions.append(tx)
        return tx

    def mine_block(self, miner_address: str) -> Block:
        """Minera um novo bloco e credita recompensa ao minerador"""
        reward_tx = Transaction(
            sender="coinbase",
            recipient=miner_address,
            amount=self.block_reward
        )

        with self.lock:
            txs = [reward_tx] + self.pending_transactions.copy()
            self.pending_transactions.clear()

        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            transactions=[tx.to_dict() for tx in txs],
            previous_hash=self.last_block.hash,
            miner=miner_address,
            reward=self.block_reward,
        )

        # Proof of Work
        target = "0" * self.DIFFICULTY
        while not new_block.hash.startswith(target):
            new_block.nonce += 1
            new_block.hash = new_block.calculate_hash()

        # Aplicar transações nos saldos
        with self.lock:
            for tx_dict in new_block.transactions:
                recipient = tx_dict["recipient"]
                sender = tx_dict["sender"]
                amount = tx_dict["amount"]

                if sender != "coinbase":
                    self.balances[sender] = self.balances.get(sender, 0) - amount

                self.balances[recipient] = self.balances.get(recipient, 0) + amount

            self.chain.append(new_block)

        return new_block

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False

        return True

    def get_chain_data(self) -> Dict:
        return {
            "name": self.NAME,
            "symbol": self.SYMBOL,
            "length": len(self.chain),
            "difficulty": self.DIFFICULTY,
            "block_reward": self.block_reward,
            "is_valid": self.is_chain_valid(),
            "total_supply": sum(self.balances.values()),
            "pending_transactions": len(self.pending_transactions),
            "blocks": [b.to_dict() for b in self.chain[-10:]],  # últimos 10
        }
