"""
Writer's Block Blockchain — v0 demo.
Three writers write. Their strokes are counted. Blocks seal.
The chain publishes its miners and pays them by the stroke.

Run:  python3 demo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wbc.chain import WritersBlockChain, UNIT  # noqa: E402

STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo-chain.json")
if os.path.exists(STORE):
    os.remove(STORE)

chain = WritersBlockChain(store_path=STORE)

WRITERS = [
    ("Mara Venn", "The Reading of the Will",
     "The lawyer cleared his throat and the room went cold. Everything "
     "Margaret Williams owned now belonged to a piece of paper, and the "
     "paper had opinions. Deke watched the executor's hands, steady as a "
     "metronome, turning pages that turned people into property. Outside, "
     "the streetlights hummed in a key nobody had chosen. Mara counted "
     "the strokes of the pen the way other people count exits."),
    ("Deke Pryor", "Mortgage",
     "They came at dawn because dawn is when a house is weakest. Ro stood "
     "in the doorway with his grandfather's watch in his fist, measuring "
     "the seconds the way the bank measured his life, in arrears. The "
     "Remainder did not knock. Paper men never knock; they file. But the "
     "house had a groove in it that morning, a slip in the rhythm, and "
     "for one held breath the eviction could not find the beat."),
    ("Wren", "Standing",
     "I am nine years old and I can prove I am a person. I have a laugh "
     "that my grandmother gave me and a name that is mine even if no "
     "ledger wants it. The lady with the steady hands says the court "
     "counts strokes, so I am writing this big. Every letter is a "
     "stroke. Every stroke is me, standing. Count them. I dare you."),
    ("Mara Venn", "The Count",
     "One hundred and twelve. That is how many places the estate had to "
     "correct its own charter because one woman filed one objection in "
     "the right margin of the world. The flaw was never the comma. The "
     "flaw was that they believed paper could hold a people. Paper tears. "
     "People, counted properly, do not. Mara sharpened her pen like a "
     "blade and began, again, to write the count out loud."),
]

print("WRITER'S BLOCK BLOCKCHAIN — proof-of-stroke demo")
print("=" * 60)
for writer, title, text in WRITERS:
    seg, sealed = chain.submit_writing(writer, title, text)
    print(f"WRITE  {writer} — \"{title}\": {seg.strokes} strokes counted")
    if sealed:
        print(f"  >> BLOCK {sealed.index} SEALED — {sealed.total_strokes} "
              f"strokes, hash {sealed.hash[:16]}…")
        for w, amt in sealed.rewards.items():
            print(f"     paid {w}: {amt} {UNIT}")

print("=" * 60)
ok, msg = chain.verify()
print("VERIFY:", msg if ok else f"FAILED — {msg}")
print()
print("PUBLISHED WRITERS (the chain publishes its miners):")
for w in chain.published_writers():
    works = "; ".join(f"\"{x['title']}\" (block {x['block']})" for x in w["works"])
    print(f"- {w['writer']}: {w['strokes']} strokes, earned {w['earned']} {UNIT}")
    print(f"    works: {works}")
pending = sum(s.strokes for s in chain.pending)
print()
print(f"Pending pool: {pending} strokes toward the next block.")
