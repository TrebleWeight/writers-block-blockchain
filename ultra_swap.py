"""Gasless USDC -> SOL swap via Jupiter Ultra (JupiterZ RFQ).

The launch wallet holds USDC but 0 SOL, so it cannot pay its own
transaction fee. Ultra's JupiterZ route is filled by a market maker:
the fee (2 bps) comes out of the trade and the maker's account pays
the network fee. This script verifies the fee payer is NOT the launch
wallet before signing, then executes through Ultra.
"""
import base64
import json
import sys
import time
import urllib.request

RPC = "https://api.mainnet-beta.solana.com"
ULTRA = "https://api.jup.ag/ultra/v1"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
SOL = "So11111111111111111111111111111111111111112"
AMOUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 4_518_017


def http_json(url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "wbc-launch/1.0"},
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read())


def http_json_lenient(url, payload=None):
    """Like http_json but returns the error body instead of raising."""
    import urllib.error

    try:
        return http_json(url, payload)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        return {"_http_error": e.code, "_body": body[:800]}


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
    print("SOL lamports before:", rpc("getBalance", [me])["result"]["value"])

    order = http_json(
        f"{ULTRA}/order?inputMint={USDC}&outputMint={SOL}&amount={AMOUNT}&taker={me}"
    )
    if "transaction" not in order or not order["transaction"]:
        print("ORDER FAILED:", json.dumps(order)[:600])
        return
    labels = [p.get("swapInfo", {}).get("label") for p in order.get("routePlan", [])]
    print("route:", labels, "| out (lamports):", order.get("outAmount"),
          "| feeBps:", order.get("feeBps"), "| requestId:", order.get("requestId"))

    raw = base64.b64decode(order["transaction"])
    tx = VersionedTransaction.from_bytes(raw)
    fee_payer = str(tx.message.account_keys[0])
    print("fee payer:", fee_payer)
    if fee_payer == me:
        print("NOT GASLESS: fee payer is the launch wallet. Aborting.")
        return

    # Sign the message bytes exactly as they appear on the wire. In this
    # solders version, bytes(tx.message) omits the 0x80 version prefix,
    # which silently invalidates the signature; the raw transaction tail
    # (after the signature block) is the true payload.
    nsigs = raw[0]
    wire_msg = raw[1 + 64 * nsigs:]
    sig = kp.sign_message(wire_msg)
    keys = [str(k) for k in tx.message.account_keys]
    idx = keys.index(me)
    sigs = list(tx.signatures)
    sigs[idx] = sig
    signed = VersionedTransaction.populate(tx.message, sigs)

    result = http_json_lenient(
        f"{ULTRA}/execute",
        {
            "signedTransaction": base64.b64encode(bytes(signed)).decode(),
            "requestId": order["requestId"],
        },
    )
    print("execute result:", json.dumps(result)[:600])
    if result.get("status") != "Success":
        print("EXECUTE DID NOT SUCCEED")
        return

    for _ in range(15):
        bal = rpc("getBalance", [me])["result"]["value"]
        if bal > 0:
            break
        time.sleep(2)
    print("SOL lamports after:", bal)
    print("ULTRA SWAP DONE, tx:", result.get("signature"))


if __name__ == "__main__":
    main()
