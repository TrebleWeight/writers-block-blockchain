"""
Writer's Block Blockchain — settlement layer (v0)
Copyright (c) 2026 Pensativity Solutions LLC. All rights reserved.

The founder's architecture (Nov 23, 2026):
  - SOLANA works the chain: every sealed WBC block is stamped onto Solana
    as a memo transaction — the block's hash, stroke count, and writer
    count become a public, timestamped record anyone can verify.
  - ETHEREUM anchors it: the same block hash is prepared as an Ethereum
    transaction payload (0-value self-transfer, hash as calldata) for the
    founder to sign from his own wallet — permanence on the prestige chain.
    Ethereum payloads are CONSTRUCTED here, never sent: sending needs the
    founder's key and his yes, and this module holds neither.

Solana side runs on DEVNET — real chain mechanics, test money. Transport is
raw JSON-RPC with long timeouts and retries: the public devnet endpoint is
slow from some networks, and this layer is built to survive that.
"""

import base64
import json
import os
import time
import urllib.request

from solders.hash import Hash as SolHash
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

MEMO_PROGRAM_ID = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
DEVNET_URL = "https://api.devnet.solana.com"
HERE = os.path.dirname(os.path.abspath(__file__))
KEYPAIR_PATH = os.path.join(HERE, "..", "devnet-keypair.json")

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + _B58.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + raw


def _hash_from_string(s: str) -> SolHash:
    try:
        return SolHash.from_string(s)
    except Exception:
        return SolHash(_b58decode(s))


def rpc(url: str, method: str, params: list, timeout=60, retries=3):
    body = json.dumps({"jsonrpc": "2.0", "id": 1,
                       "method": method, "params": params}).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            if "error" in data:
                raise RuntimeError(f"{method}: {data['error']}")
            return data["result"]
        except Exception as e:  # slow public endpoint — back off and retry
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{method} failed after {retries} tries: {last}")


def anchor_memo(block) -> str:
    """The text stamped onto Solana for one sealed WBC block."""
    writers = sorted({s.writer for s in block.segments})
    return (f"WBC block {block.index} | hash {block.hash} | "
            f"strokes {block.total_strokes} | writers {len(writers)}: "
            f"{', '.join(writers)}")


def load_or_create_devnet_keypair():
    """A project keypair for DEVNET ONLY. It holds no real funds and never
    will — mainnet signing is the founder's wallet, not this file."""
    if os.path.exists(KEYPAIR_PATH):
        with open(KEYPAIR_PATH) as f:
            secret = json.load(f)["secret_key_bytes"]
        return Keypair.from_bytes(bytes(secret))
    kp = Keypair()
    with open(KEYPAIR_PATH, "w") as f:
        json.dump({
            "warning": "DEVNET ONLY — test keypair, no real funds, never fund on mainnet",
            "public_key": str(kp.pubkey()),
            "secret_key_bytes": list(bytes(kp)),
        }, f, indent=1)
    return kp


class SolanaAnchor:
    def __init__(self, url=DEVNET_URL):
        self.url = url
        self.keypair = load_or_create_devnet_keypair()

    @property
    def pubkey(self):
        return self.keypair.pubkey()

    def balance_sol(self):
        return rpc(self.url, "getBalance", [str(self.pubkey)])["value"] / 1e9

    def ensure_funds(self):
        if self.balance_sol() >= 0.05:
            return
        rpc(self.url, "requestAirdrop", [str(self.pubkey), 1_000_000_000])
        for _ in range(30):
            time.sleep(3)
            if self.balance_sol() >= 0.05:
                return
        raise RuntimeError("devnet airdrop did not land in time")

    def _wait_confirmed(self, signature: str, tries=40):
        for _ in range(tries):
            res = rpc(self.url, "getSignatureStatuses", [[signature]])
            status = res["value"][0]
            if status and status.get("confirmationStatus") in (
                    "confirmed", "finalized"):
                if status.get("err"):
                    raise RuntimeError(f"tx failed on-chain: {status['err']}")
                return True
            time.sleep(3)
        return False

    def anchor_block(self, block) -> str:
        memo = anchor_memo(block)
        ix = Instruction(MEMO_PROGRAM_ID, memo.encode("utf-8"), [])
        bh = rpc(self.url, "getLatestBlockhash",
                 [{"commitment": "finalized"}])["value"]["blockhash"]
        blockhash = _hash_from_string(bh)
        msg = Message.new_with_blockhash([ix], self.pubkey, blockhash)
        txn = Transaction([self.keypair], msg, blockhash)
        wire = base64.b64encode(bytes(txn)).decode()
        sig = rpc(self.url, "sendTransaction",
                  [wire, {"encoding": "base64", "maxRetries": 5}])
        if not self._wait_confirmed(sig):
            raise RuntimeError(f"anchor tx {sig} not confirmed in time")
        return sig

    def verify_anchor(self, signature: str, block) -> bool:
        res = rpc(self.url, "getTransaction",
                  [signature, {"encoding": "json",
                               "maxSupportedTransactionVersion": 0}])
        if not res:
            return False
        logs = (res.get("meta") or {}).get("logMessages") or []
        return any(anchor_memo(block) in log for log in logs)

    def run(self, blocks):
        self.ensure_funds()
        records = {"_wallet": {"pubkey": str(self.pubkey),
                               "balance_sol": self.balance_sol()}}
        for block in blocks:
            sig = self.anchor_block(block)
            records[block.index] = {
                "solana_signature": sig,
                "memo": anchor_memo(block),
                "verified": self.verify_anchor(sig, block),
            }
        return records


def ethereum_anchor_payload(block, founder_address: str) -> dict:
    """The Ethereum anchor, constructed and ready for the founder's
    signature — a 0-value transaction from his wallet to itself carrying
    the block hash as calldata. NOT sent by this module, ever."""
    return {
        "network": "ethereum-mainnet",
        "status": "UNSIGNED — awaiting founder signature",
        "from": founder_address,
        "to": founder_address,
        "value_eth": 0,
        "data_calldata": "0x" + block.hash,
        "memo": f"WBC block {block.index} anchor — {block.total_strokes} strokes",
        "note": "Signing this from the founder's wallet stamps the block "
                "hash into Ethereum history permanently. Gas at time of "
                "signing is the only cost.",
    }
