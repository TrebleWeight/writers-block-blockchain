"""Swap some of the launch wallet's USDC to SOL via Jupiter.

The launch wallet holds USDC (sent from FOMO, which only withdraws USDC)
but 0 SOL, and every Solana transaction needs SOL for its fee. JupiterZ
(RFQ) quotes are filled by a market maker who pays the network fee, so
this script checks who the fee payer is before signing: if the fee payer
is the launch wallet itself, the swap cannot work and nothing is sent.
"""
import base64
import json
import sys
import time
import urllib.request

RPC = "https://api.mainnet-beta.solana.com"
JUP = "https://lite-api.jup.ag/swap/v1"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOL = "So11111111111111111111111111111111111111112"
AMOUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 2_000_000  # 2 USDC


def http_json(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "wbc-launch/1.0"},
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read())


def rpc(method, params):
    return http_json(RPC, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})


def main():
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction

    with open("mainnet-keypair.json") as f:
        data = json.load(f)
    secret = data["secret"] if isinstance(data, dict) else data
    kp = Keypair.from_bytes(bytes(secret))
    me = str(kp.pubkey())
    print("wallet:", me)

    bal = rpc("getBalance", [me])["result"]["value"]
    print("SOL lamports before:", bal)

    quote = http_json(
        f"{JUP}/quote?inputMint={USDC}&outputMint={SOL}&amount={AMOUNT}&slippageBps=100"
    )
    if "outAmount" not in quote:
        print("QUOTE FAILED:", json.dumps(quote)[:500])
        return
    labels = [p.get("swapInfo", {}).get("label") for p in quote.get("routePlan", [])]
    print("quote out (lamports):", quote["outAmount"], "route:", labels)

    swap = http_json(
        f"{JUP}/swap",
        {
            "quoteResponse": quote,
            "userPublicKey": me,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
        },
    )
    if "swapTransaction" not in swap:
        print("SWAP BUILD FAILED:", json.dumps(swap)[:500])
        return

    raw = base64.b64decode(swap["swapTransaction"])
    tx = VersionedTransaction.from_bytes(raw)
    fee_payer = str(tx.message.account_keys[0])
    print("fee payer:", fee_payer)
    if fee_payer == me:
        print("NOT GASLESS: fee payer is the launch wallet, which holds 0 SOL. Aborting.")
        return

    # Sign in place, preserving any existing (market maker) signatures.
    sig = kp.sign_message(bytes(tx.message))
    keys = [str(k) for k in tx.message.account_keys]
    idx = keys.index(me)
    sigs = list(tx.signatures)
    sigs[idx] = sig
    signed = VersionedTransaction.populate(tx.message, sigs)

    sent = rpc(
        "sendTransaction",
        [base64.b64encode(bytes(signed)).decode(), {"encoding": "base64", "maxRetries": 3}],
    )
    if "error" in sent:
        print("SEND FAILED:", json.dumps(sent["error"])[:500])
        return
    signature = sent["result"]
    print("tx sent:", signature)

    for _ in range(30):
        time.sleep(2)
        st = rpc("getSignatureStatuses", [[signature]])["result"]["value"][0]
        if st and st.get("confirmationStatus") in ("confirmed", "finalized"):
            if st.get("err"):
                print("TX ERRORED:", st["err"])
                return
            break
    else:
        print("TX NOT CONFIRMED IN TIME")
        return

    bal = rpc("getBalance", [me])["result"]["value"]
    print("SOL lamports after:", bal)
    print("SWAP DONE")


if __name__ == "__main__":
    main()
