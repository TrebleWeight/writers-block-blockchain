"""
Anchor the demo chain's sealed blocks: Solana stamps them, Ethereum
payloads are prepared for the founder's signature.
Run:  python3 anchor_demo.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wbc.chain import WritersBlockChain  # noqa: E402
from wbc.settlement import SolanaAnchor, ethereum_anchor_payload  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FOUNDER_ETH = "0x9Bf700ccC46940aC155A0b3083ab4b160fF88Fe6"  # public address


def main():
    chain = WritersBlockChain(store_path=os.path.join(HERE, "demo-chain.json"))
    sealed = [b for b in chain.blocks if b.index > 0]
    print(f"Chain loaded: {len(sealed)} sealed blocks to settle", flush=True)

    anchor = SolanaAnchor()
    print(f"Solana devnet wallet: {anchor.pubkey}", flush=True)
    records = anchor.run(sealed)
    wallet = records.pop("_wallet")
    print(f"Devnet balance: {wallet['balance_sol']} SOL (test money)", flush=True)

    for idx, rec in records.items():
        print(f"Block {idx}: anchored on Solana devnet", flush=True)
        print(f"  signature: {rec['solana_signature']}")
        print(f"  explorer:  https://explorer.solana.com/tx/"
              f"{rec['solana_signature']}?cluster=devnet")
        print(f"  read-back verification: "
              f"{'MEMO MATCHES BLOCK' if rec['verified'] else 'FAILED'}")

    out = {
        "solana_devnet": {"wallet": wallet, "anchors": records},
        "ethereum_payloads": {
            str(b.index): ethereum_anchor_payload(b, FOUNDER_ETH)
            for b in sealed
        },
    }
    with open(os.path.join(HERE, "settlement-record.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("Settlement record saved: settlement-record.json")
    print("Ethereum payloads: constructed, UNSIGNED — founder signs when ready.")


if __name__ == "__main__":
    main()
