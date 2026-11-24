"""
Writer's Block Blockchain — MAINNET runner (v0)
Copyright (c) 2026 Pensativity Solutions LLC. All rights reserved.

The same flow as the devnet Writer Prompt Bot, pointed at Solana MAINNET
and the real WBB mint (HqUfKmTZz5199C975hEwG6yGNXdaJVSuThgBFGu4a5Gs):

  1. A writer's piece enters the mainnet chain's pool (strokes + words
     counted; a block seals at 1,000 pooled words — founder's rule,
     Nov 23, 2026).
  2. On seal, the block is stamped onto Solana mainnet as a memo
     transaction and verified by read-back.
  3. Each writer's share of the 50 WBB block reward is minted into their
     writer wallet — the first WBB in existence are born this way; the
     mint launched with supply 0 by design.

Signing: the project launch wallet (mainnet-keypair.json, launch funds
only; custody transfer to the founder pending). Writer wallets are
project-custodied until a writer claims theirs.

Usage:
  python3 mainnet_bot.py --check    read-only readiness report (no txs)
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solders.keypair import Keypair  # noqa: E402
from solders.pubkey import Pubkey  # noqa: E402

from wbc.chain import WritersBlockChain  # noqa: E402
from wbc.settlement import SolanaAnchor, rpc  # noqa: E402
from wbc.token import WbcToken  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAINNET_URL = "https://api.mainnet-beta.solana.com"
MAINNET_KEYPAIR = os.path.join(HERE, "mainnet-keypair.json")
MAINNET_RECORD = os.path.join(HERE, "mainnet-token-record.json")
CHAIN_PATH = os.path.join(HERE, "mainnet-chain.json")
WRITER_WALLETS = os.path.join(HERE, "mainnet-writer-wallets.json")


def load_mainnet_keypair():
    with open(MAINNET_KEYPAIR) as f:
        data = json.load(f)
    secret = data.get("secret") or data.get("secret_key_bytes")
    return Keypair.from_bytes(bytes(secret))


def load_mainnet_mint():
    with open(MAINNET_RECORD) as f:
        return Pubkey.from_string(json.load(f)["mint"])


def load_or_create_writer_wallets(names, path):
    """Writer wallets for MAINNET. Project-custodied until claimed."""
    wallets = {}
    if os.path.exists(path):
        with open(path) as f:
            stored = json.load(f)
        for name, secret in stored["wallets"].items():
            wallets[name] = Keypair.from_bytes(bytes(secret))
    changed = False
    for name in names:
        if name not in wallets:
            wallets[name] = Keypair()
            changed = True
    if changed or not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({
                "warning": "MAINNET writer wallets — project-custodied "
                           "keys holding real WBB until each writer "
                           "claims theirs. Handle with care.",
                "wallets": {n: list(bytes(kp)) for n, kp in wallets.items()},
            }, f, indent=1)
    return wallets


class MainnetBot:
    def __init__(self):
        self.keypair = load_mainnet_keypair()
        self.chain = WritersBlockChain(store_path=CHAIN_PATH)
        self.anchor = SolanaAnchor(url=MAINNET_URL)
        self.anchor.keypair = self.keypair  # launch wallet signs anchors
        self.token = WbcToken(self.keypair, url=MAINNET_URL)
        self.token.mint = load_mainnet_mint()

    # --- read-only readiness ---------------------------------------------
    def check(self):
        bal = rpc(MAINNET_URL, "getBalance",
                  [str(self.keypair.pubkey())])["value"] / 1e9
        supply = rpc(MAINNET_URL, "getTokenSupply",
                     [str(self.token.mint)])["value"]["uiAmountString"]
        pool_words = sum(s.words for s in self.chain.pending)
        pool_strokes = sum(s.strokes for s in self.chain.pending)
        ok, msg = self.chain.verify()
        return {
            "wallet": str(self.keypair.pubkey()),
            "wallet_sol": bal,
            "mint": str(self.token.mint),
            "wbb_supply": supply,
            "sealed_blocks": len(self.chain.blocks) - 1,
            "pool_words": pool_words,
            "pool_strokes": pool_strokes,
            "chain": msg if ok else f"FAILED — {msg}",
        }

    # --- writing / mining --------------------------------------------------
    def submit(self, writer, title, text):
        seg, sealed = self.chain.submit_writing(writer, title, text)
        report = {"writer": writer, "title": title, "words": seg.words,
                  "strokes": seg.strokes, "sealed": None}
        if sealed:
            report["sealed"] = self._settle(sealed)
        return report

    def _settle(self, block):
        sig = self.anchor.anchor_block(block)
        verified = self.anchor.verify_anchor(sig, block)
        names = list(block.rewards.keys())
        wallets = load_or_create_writer_wallets(names, WRITER_WALLETS)
        payments = {}
        for name, earned in block.rewards.items():
            self.token.pay_writer(wallets[name].pubkey(), earned)
            payments[name] = {
                "earned": earned,
                "balance": self.token.balance(wallets[name].pubkey()),
                "wallet": str(wallets[name].pubkey()),
            }
        return {"block": block.index, "words": block.total_words,
                "strokes": block.total_strokes, "solana_signature": sig,
                "anchor_verified": verified, "payments": payments}

    def ledger(self):
        return self.chain.published_writers()


if __name__ == "__main__":
    bot = MainnetBot()
    if "--check" in sys.argv:
        r = bot.check()
        print("MAINNET READINESS — Writer's Block Blockchain")
        print(f"  launch wallet : {r['wallet']}")
        print(f"  wallet balance: {r['wallet_sol']} SOL")
        print(f"  WBB mint      : {r['mint']}")
        print(f"  WBB supply    : {r['wbb_supply']}")
        print(f"  sealed blocks : {r['sealed_blocks']}")
        print(f"  pool          : {r['pool_words']} words "
              f"({r['pool_strokes']} strokes) toward Block 1")
        print(f"  chain         : {r['chain']}")
    else:
        print("Read-only by default. Use --check, or drive submissions "
              "from a session script once the founder names the writers.")
