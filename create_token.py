"""
Create the WBC token on Solana devnet and pay the demo chain's writers
their earned rewards in it. Run:  /tmp/wbcvenv/bin/python create_token.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wbc.chain import WritersBlockChain  # noqa: E402
from wbc.settlement import SolanaAnchor  # noqa: E402
from wbc.token import WbcToken, load_or_create_writer_wallets  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

chain = WritersBlockChain(store_path=os.path.join(HERE, "demo-chain.json"))
ledger = chain.published_writers()

anchor = SolanaAnchor()
token = WbcToken(anchor.keypair)
if token.mint is None:
    mint, sig = token.create_mint()
    print(f"TOKEN MINT CREATED: {mint}")
    print(f"  creation tx: {sig}")
else:
    print(f"Token mint exists: {token.mint}")

names = [w["writer"] for w in ledger]
wallets = load_or_create_writer_wallets(
    names, os.path.join(HERE, "writer-wallets.json"))

print("Paying writers their chain earnings, in the token:")
for w in ledger:
    kp = wallets[w["writer"]]
    ata, sig = token.pay_writer(kp.pubkey(), w["earned"])
    bal = token.balance(kp.pubkey())
    print(f"- {w['writer']}: earned {w['earned']} -> balance {bal}")
    print(f"    wallet {kp.pubkey()} · tx {sig}")
print("Explorer (devnet): https://explorer.solana.com/address/"
      f"{token.mint}?cluster=devnet")
