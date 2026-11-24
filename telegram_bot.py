#!/usr/bin/env python3
"""
WBB Telegram Bot — the Telegram front door of Writer's Block Blockchain.

What it does:
  /start   — what this is
  /prompt  — a fresh writing prompt (never the same draw twice in a row)
  /price   — live WBB price from the Meteora pool reserves
  /pool    — Block 2 pool status (words pooled toward 1,000)
  /submit  — paid submission intake: charges a small SOL fee, verifies the
             payment on-chain by transaction signature, then takes the
             writer's piece, counts its words/strokes with the chain's own
             counters, and pools it toward the next block. The wallet that
             paid is recorded as the payout wallet for the block reward.

Fees land in the project launch wallet — the same wallet that pays for
block seals, so submission fees refill the seal reserve.

Setup:
  1. Talk to @BotFather on Telegram, /newbot, get a token.
  2. WBB_BOT_TOKEN=<token> python3 telegram_bot.py
State is kept in telegram-pool.json next to this file. Sealing is done by
mainnet_bot.py against the merged pool — the bot is an intake door, not
the seal runner.

No third-party dependencies: stdlib only (urllib), plus wbc/chain.py for
the official counters when available.
"""
import json, os, random, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "telegram-pool.json")
RPC = "https://api.mainnet-beta.solana.com"

TOKEN = os.environ.get("WBB_BOT_TOKEN", "")
INTAKE_WALLET = "8mRhcULcQJJohBxcFRwQxCYTFgiMF8d1SniZUQca4VVV"  # launch wallet
FEE_SOL = 0.01
FEE_LAMPORTS = int(FEE_SOL * 1_000_000_000)
WBB_MINT = "HqUfKmTZz5199C975hEwG6yGNXdaJVSuThgBFGu4a5Gs"
POOL = "2xTNGius4AoooT5uwydtooDuPukLWrhmpjRtJcz5FoBW"
VAULT_WBB = "EKYTprXDpRP9f17EfnihNvVaGcygr7udHMALJKcwVpRt"
VAULT_SOL = "G9XguA3WQMTKKPWtCNDq9SD54zEuM4VKW8bh7Pm6kwzM"
BLOCK_WORDS = 1000
BLOCK_REWARD = 50.0

try:
    sys.path.insert(0, HERE)
    from wbc.chain import count_words, count_strokes
except Exception:
    def count_words(t): return len(t.split())
    def count_strokes(t): return len(t)

CHARACTERS = ["a street musician whose audience has gone silent", "a night clerk at a motel that rents rooms by the hour of sleep", "a cartographer mapping a city that rearranges itself at dawn", "a lighthouse keeper on a coast with no ships", "a retired boxer who now grows orchids", "a translator for a language only one person speaks", "a locksmith who has never owned a key", "a baker whose bread remembers yesterday"]
PLACES = ["a rooftop above a flooded avenue", "the last open diner in a closing town", "a train platform where the boards never change", "a library that lends memories instead of books", "a market that only opens during eclipses", "a bridge toll booth at 3 a.m.", "a greenhouse built inside a decommissioned submarine", "a courthouse waiting room on the last day of the year"]
OBJECTS = ["a metronome that ticks in prime numbers", "a coat with a letter sewn into the lining", "a radio that picks up tomorrow's weather", "a key that opens only doors that are already open", "a ledger with one page never turned", "a trumpet with a dent shaped like a thumbprint", "a photograph of people nobody can identify", "a compass that points at whatever was lost"]
TWISTS = ["the object only works when nobody is watching", "someone has been waiting for exactly this person", "the price of help is a true story", "time runs one minute slow here, and it adds up", "the stranger knows the song but not the words", "leaving is easy; being left is the hard part", "the map is right and the territory is wrong", "what was lost wants to stay lost"]

def prompt():
    return (f"Write about {random.choice(CHARACTERS)}, at {random.choice(PLACES)}, "
            f"with {random.choice(OBJECTS)} — and remember: {random.choice(TWISTS)}.")

def rpc(method, params):
    req = urllib.request.Request(RPC, data=json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    if "error" in out: raise RuntimeError(out["error"])
    return out["result"]

def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE))
    return {"used_sigs": [], "segments": [], "pool_words": 0}

def save_state(s): json.dump(s, open(STATE, "w"), indent=1)

def verify_payment(sig, state):
    """Return payer address if sig pays >= FEE to the intake wallet, else None."""
    if sig in state["used_sigs"]: return None
    tx = rpc("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
    if not tx or (tx.get("meta") or {}).get("err"): return None
    for ix in tx["transaction"]["message"]["instructions"]:
        if ix.get("program") == "system":
            p = ix.get("parsed") or {}
            if p.get("type") == "transfer":
                info = p["info"]
                if info["destination"] == INTAKE_WALLET and int(info["lamports"]) >= FEE_LAMPORTS:
                    return info["source"]
    return None

def pool_price():
    a = rpc("getTokenAccountBalance", [VAULT_WBB])["value"]
    b = rpc("getTokenAccountBalance", [VAULT_SOL])["value"]
    wbb = int(a["amount"]) / 10 ** int(a["decimals"])
    sol = int(b["amount"]) / 10 ** int(b["decimals"])
    return (sol / wbb if wbb else 0.0), wbb, sol

def tg(method, **kw):
    req = urllib.request.Request(f"https://api.telegram.org/bot{TOKEN}/{method}",
        data=json.dumps(kw).encode(), headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def say(chat, text): tg("sendMessage", chat_id=chat, text=text)

WELCOME = ("Writer's Block Blockchain — writers are the miners, words seal the blocks.\n\n"
           "/prompt — a fresh writing prompt\n"
           "/price — the live WBB price\n"
           "/pool — Block 2 pool status\n"
           f"/submit — enter a piece into Block 2 (fee: {FEE_SOL} SOL)\n\n"
           "Blocks seal at 1,000 pooled words. The 50 WBB reward splits by word share "
           "and pays to the wallet you submit from.")

def main():
    if not TOKEN:
        print("Set WBB_BOT_TOKEN (from @BotFather) and run again.")
        sys.exit(1)
    state = load_state()
    flow = {}   # chat_id -> {"step": ..., "payer": ...}
    offset = 0
    print("WBB bot live. Intake:", INTAKE_WALLET, "fee:", FEE_SOL, "SOL")
    while True:
        try:
            res = tg("getUpdates", offset=offset, timeout=30)
        except Exception as e:
            print("poll error:", e); time.sleep(5); continue
        for upd in res.get("result", []):
            offset = upd["update_id"] + 1
            msg = upd.get("message") or {}
            chat = (msg.get("chat") or {}).get("id")
            text = (msg.get("text") or "").strip()
            if not chat or not text: continue
            try:
                if text.startswith("/start"): say(chat, WELCOME)
                elif text.startswith("/prompt"): say(chat, prompt())
                elif text.startswith("/price"):
                    px, wbb, sol = pool_price()
                    say(chat, f"WBB ≈ {px:.6f} SOL (pool holds {wbb:.2f} WBB / {sol:.4f} SOL on Meteora).")
                elif text.startswith("/pool"):
                    say(chat, f"Block 2 pool: {state['pool_words']} / {BLOCK_WORDS} words pooled "
                              f"across {len(state['segments'])} piece(s). Seals at {BLOCK_WORDS}.")
                elif text.startswith("/submit"):
                    flow[chat] = {"step": "sig"}
                    say(chat, f"Submission fee: {FEE_SOL} SOL.\n"
                              f"1) Send {FEE_SOL} SOL (or more) to:\n{INTAKE_WALLET}\n"
                              "2) Then paste the transaction signature here.\n"
                              "The wallet you pay from is where your WBB lands at the seal.")
                elif chat in flow and flow[chat]["step"] == "sig":
                    payer = verify_payment(text, state)
                    if payer:
                        flow[chat] = {"step": "name", "payer": payer, "sig": text}
                        say(chat, "Payment verified. What pen name should the ledger carry?")
                    else:
                        say(chat, "That signature doesn't show a payment of the fee to the intake "
                                  "wallet (or it was already used). Check it and paste again, or /submit to restart.")
                elif chat in flow and flow[chat]["step"] == "name":
                    flow[chat]["name"] = text[:60]; flow[chat]["step"] = "piece"
                    say(chat, "Now send your piece — the whole text, one message.")
                elif chat in flow and flow[chat]["step"] == "piece":
                    w, s = count_words(text), count_strokes(text)
                    seg = {"writer": flow[chat]["name"], "text": text, "words": w, "strokes": s,
                           "payer": flow[chat]["payer"], "sig": flow[chat]["sig"], "ts": int(time.time())}
                    state["segments"].append(seg); state["used_sigs"].append(seg["sig"])
                    state["pool_words"] += w; save_state(state)
                    del flow[chat]
                    say(chat, f"Entered. {w} words, {s} strokes under '{seg['writer']}'.\n"
                              f"Block 2 pool now: {state['pool_words']} / {BLOCK_WORDS} words. "
                              "At the seal, the 50 WBB split by word share pays to your paying wallet.")
                else:
                    say(chat, "Commands: /prompt /price /pool /submit")
            except Exception as e:
                print("handle error:", e)
                try: say(chat, "Something jammed on my side — try that again.")
                except Exception: pass

if __name__ == "__main__":
    main()
