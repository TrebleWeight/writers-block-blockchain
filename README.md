# Writer's Block Blockchain (WBB)

**Writers are the miners. Words seal the blocks.**

Writer's Block Blockchain is a Solana-based chain where the proof-of-work is
writing itself. Writers submit original pieces; every keystroke is counted as
proof-of-stroke and every word pools toward the next block. When the pool
crosses **1,000 words**, the block seals, is stamped on Solana, and a fixed
reward of **50 WBB** is minted and split among the block's writers **by word
share**. There is no pre-mine: WBB supply is born only as block rewards.

A Pensativity Solutions LLC project.

## Live on mainnet

- **Token:** Writer's Block Blockchain (WBB)
- **Mint:** `HqUfKmTZz5199C975hEwG6yGNXdaJVSuThgBFGu4a5Gs` (4 decimals)
- **Market:** WBB/SOL pool on Meteora DAMM v2 —
  `2xTNGius4AoooT5uwydtooDuPukLWrhmpjRtJcz5FoBW` (opened Nov 24, 2026,
  seeded from the founder's own Block 1 reward)
- **Block 1:** sealed Nov 24, 2026 — 1,118 words, 6,029 strokes, anchored on
  Solana mainnet; the first 50 WBB went to its writer.
- **Writing Room (public home):** https://melodious-cactus-c9136a.netlify.app/

## How it works

1. A writer gets a fresh prompt and writes a piece.
2. The piece is counted — strokes (keystrokes) as the proof, words as the
   weight — and pooled under the writer's name.
3. At 1,000 pooled words the block seals: contents are hash-linked to the
   previous block, the seal is anchored to Solana with a memo stamp, and
   50 WBB are minted, split by each writer's share of the block's words.
4. Sealed pieces enter the published writers' ledger.

## Code map

- `wbc/chain.py` — the engine: proof-of-stroke counting, word pooling,
  block sealing, hash-linked chain, tamper verification, writers' ledger.
- `wbc/settlement.py` — Solana memo anchoring + Ethereum anchor payloads.
- `wbc/token.py` — SPL token operations (mint creation, writer payouts).
- `writer_bot.py` — interactive writer prompt bot (devnet-proven flow).
- `mainnet_bot.py` — the mainnet runner: pools submissions, seals blocks,
  anchors them, and pays writers on Solana mainnet.
- `launch_mainnet.py` — the mainnet mint launch (no pre-mine).
- `pool/pool_status.js` — read-only Meteora pool status (reserves, price,
  supply).
- `telegram_bot.py` — Telegram front door: prompts, paid submission intake
  (SOL), pool status.
- `records/` — public on-chain records: token, settlement, pool.

## Run the demo

```bash
python3 demo.py          # seals demo blocks locally, verifies the chain
python3 writer_bot.py    # prompt -> write -> seal -> anchor -> payout flow
node pool/pool_status.js # live pool reserves and spot price
```

## Security

Keypairs and writer-wallet files are **never** committed (see `.gitignore`).
The mint authority is held by the project launch wallet by design: it is the
only minter, and it mints only the 50 WBB block reward at a seal.
