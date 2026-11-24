"""
Writer's Block Blockchain — the Writer Prompt Bot (v0)
Copyright (c) 2026 Pensativity Solutions LLC. All rights reserved.

The encouragement engine, in the founder's words: the chain "encourages
and publishes" its miners. This bot is how a writer meets the chain:

  1. The bot offers a prompt.
  2. The writer writes. Every keystroke is a stroke, counted live.
  3. The writing enters the chain's pool under the writer's name.
  4. When the pool crosses the seal threshold, the block seals: the bot
     stamps it onto Solana and mints each writer's share of the block
     reward, in the WBC token, into the writer's wallet.
  5. The bot shows the published ledger — who wrote, what, and what they
     earned. To write here is to be published here.

Usage:
  python3 writer_bot.py            interactive session
  python3 writer_bot.py --demo     scripted end-to-end run (verification)
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wbc.chain import WritersBlockChain, UNIT  # noqa: E402
from wbc.settlement import SolanaAnchor  # noqa: E402
from wbc.token import WbcToken, load_or_create_writer_wallets  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CHAIN_PATH = os.path.join(HERE, "bot-chain.json")
BOT_WALLETS = os.path.join(HERE, "bot-writer-wallets.json")

PROMPTS = [
    "Write about a door that only opens for the person who built it.",
    "Write the first paragraph of the book your younger self needed.",
    "Write about a debt that money cannot settle.",
    "Write a scene where the villain is a form that must be filed correctly.",
    "Write about the hour of the day that belongs entirely to you.",
    "Write a letter to the house you grew up in. Do not send it. Seal it here.",
    "Write about a machine that runs on people believing in it.",
    "Write the moment a nobody becomes a witness.",
    "Write about a city where every streetlight hums a different note.",
    "Write a eulogy for a law that deserved to die.",
    "Write about the last honest sentence in a dishonest document.",
    "Write the sound of a frequency no instrument can play.",
]


class WriterBot:
    def __init__(self):
        self.chain = WritersBlockChain(store_path=CHAIN_PATH)
        self.anchor = SolanaAnchor()
        self.token = WbcToken(self.anchor.keypair)

    def prompt(self):
        return random.choice(PROMPTS)

    def submit(self, writer, title, text):
        """One writer answers a prompt. Returns a report dict."""
        seg, sealed = self.chain.submit_writing(writer, title, text)
        report = {"writer": writer, "title": title,
                  "strokes": seg.strokes, "sealed": None}
        if sealed:
            report["sealed"] = self._settle(sealed)
        return report

    def _settle(self, block):
        """Stamp the sealed block on Solana and pay its writers in token."""
        sig = self.anchor.anchor_block(block)
        verified = self.anchor.verify_anchor(sig, block)
        names = list(block.rewards.keys())
        wallets = load_or_create_writer_wallets(names, BOT_WALLETS)
        payments = {}
        for name, earned in block.rewards.items():
            self.token.pay_writer(wallets[name].pubkey(), earned)
            payments[name] = {
                "earned": earned,
                "balance": self.token.balance(wallets[name].pubkey()),
                "wallet": str(wallets[name].pubkey()),
            }
        return {"block": block.index, "strokes": block.total_strokes,
                "solana_signature": sig, "anchor_verified": verified,
                "payments": payments}

    def ledger(self):
        return self.chain.published_writers()


def print_report(bot, report):
    print(f"  {report['writer']} — \"{report['title']}\": "
          f"{report['strokes']} strokes counted.")
    s = report["sealed"]
    if s:
        print(f"  >> BLOCK {s['block']} SEALED ({s['strokes']} strokes) and "
              f"stamped on Solana: {s['solana_signature'][:20]}… "
              f"({'verified' if s['anchor_verified'] else 'UNVERIFIED'})")
        for name, p in s["payments"].items():
            print(f"     paid {name}: +{p['earned']} {UNIT} "
                  f"(token balance now {p['balance']})")
    else:
        pending = sum(x.strokes for x in bot.chain.pending)
        print(f"  Pool: {pending} strokes toward the next seal.")


def print_ledger(bot):
    print("\nPUBLISHED WRITERS — the chain publishes its miners:")
    for w in bot.ledger():
        works = "; ".join(f"\"{x['title']}\"" for x in w["works"])
        print(f"- {w['writer']}: {w['strokes']} strokes, "
              f"earned {w['earned']} {UNIT} — {works}")


DEMO_SESSION = [
    ("June Park", "The Door I Built",
     "The door only opens for the person who built it, so I built it out "
     "of everything they said I could not carry: a father's patience, a "
     "clerk's precision, a singer's stubborn breath. I cut the hinges "
     "from old ledger covers. I planed the frame from a pew nobody sat "
     "in anymore. When the inspectors came with their clipboards, the "
     "door was just a wall to them, and I smiled, because a wall is only "
     "a door that has not met its builder yet. Tonight I turn the handle "
     "I carved with my own initials and walk through, whistling."),
    ("Cale Mercer", "The Hour That Is Mine",
     "Four in the morning belongs to me. The city has not started lying "
     "yet. The forms are asleep in their drawers, the executors are "
     "dreaming their gray dreams, and the only ledger open is the one "
     "the sky keeps, written in a hand too large to forge. I make tea. "
     "I sharpen nothing. I let the hour be unproductive on purpose, "
     "which is the most radical filing I know: a claim staked on "
     "nothing, owned by nobody, accruing to a man the paperwork has "
     "not finished inventing. At five, the world resumes. By then I am "
     "already rich in the only currency the dead cannot probate."),
]


def run_demo():
    if os.path.exists(CHAIN_PATH):
        os.remove(CHAIN_PATH)
    bot = WriterBot()
    print("WRITER PROMPT BOT — demo session")
    print("=" * 60)
    for writer, title, text in DEMO_SESSION:
        print(f"PROMPT for {writer}: {bot.prompt()}")
        print_report(bot, bot.submit(writer, title, text))
    ok, msg = bot.chain.verify()
    print("=" * 60)
    print("CHAIN:", msg if ok else f"FAILED — {msg}")
    print_ledger(bot)


def run_interactive():
    bot = WriterBot()
    print("WRITER'S BLOCK BLOCKCHAIN — Writer Prompt Bot")
    print("Write, and the chain counts your strokes. Fill a block and it "
          "seals, stamps itself on Solana, and pays you in the token.")
    writer = input("Your writer name: ").strip() or "Anonymous"
    while True:
        print(f"\nPROMPT: {bot.prompt()}")
        title = input("Title for this piece (or 'quit'): ").strip()
        if title.lower() == "quit":
            break
        print("Write. End with a line containing only a single period.")
        lines = []
        while True:
            line = input()
            if line.strip() == ".":
                break
            lines.append(line)
        report = bot.submit(writer, title or "Untitled", "\n".join(lines))
        print_report(bot, report)
    print_ledger(bot)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        run_demo()
    else:
        run_interactive()
