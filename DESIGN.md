# Writer's Block Blockchain — Design (v0, Nov 23, 2026)
*A Pensativity Solutions build. Founder: Anthony Wilkerson. Status: working prototype, private — not publicly disclosed (IP posture preserved).*

## The idea, in the founder's words
"A blockchain that mines crypto by counting strokes and encourages and publishes 'miners or writers.'"

Every other chain burns something useless to mint value — electricity on hashes. This one burns the one work that was always valuable and never paid at the moment of making: **writing itself.** The stroke is the work. The writer is the miner. The chain is the publisher.

## The mechanism — Proof-of-Stroke (built, v0)
- **Stroke** = one keystroke producing a character. The engine counts stroke *events*, so other inputs can feed it later: pen strokes on a tablet, a typewriter key, SparkTank answers.
- **Pool**: writing arrives in segments (writer, title, text). Strokes and words are counted on arrival and credited to the writer — strokes are the proof the writing happened; words are the measure of the block.
- **Seal**: when the pool reaches the threshold — **1,000 words** (founder's change, Nov 23, 2026, superseding the original v0 500-stroke seal) — the block seals: every segment bound by hash into one block, linked to the previous block's hash. Tamper with a letter and the chain breaks loudly.
- **Reward**: each seal mints the block reward (v0: 50 units), split among the block's writers in exact proportion to words contributed. No words, no share.
- **Publishing**: the chain keeps a public ledger of its miners — every writer, every work, lifetime strokes and words, lifetime earnings. To write on it is to be published by it.

Verified Nov 23, 2026: demo run sealed 2 blocks, 1,468 strokes mined, 3 writers published and paid, chain integrity check passed. Re-verified the same day under the 1,000-word rule: the pool held at 624 and at 936 words without sealing, sealed at 1,144 words, the 50.0 reward split exactly by word share, chain valid.

## How SparkTank plugs in ("having what ST provides")
SparkTank already makes people write — the 7-step intake produces a mission statement, business plan, and due-diligence report. On Writer's Block Blockchain, that writing is no longer just an intake: **every answer a founder types is mining.** ST supplies the writers, the structure, and the reason to write; the chain supplies the count, the reward, and the publication. The SparkTank documents become the first works published on the chain, and the founder's strokes become the first mined units.

## Settlement architecture (decided Nov 23, 2026 — "Do that")
- **Solana works the chain**: every sealed block is stamped onto Solana as a memo transaction (block hash, stroke count, writers) — public, timestamped, verifiable. Fees are fractions of a cent, which is the only way stroke-level action survives.
- **Ethereum anchors it**: the same block hash is prepared as a 0-value self-transfer payload with the hash as calldata, for the founder to sign from his own wallet (0x9Bf7…Fe6) — permanence and prestige, paid rarely. Payloads are constructed by the code, never sent by it.
- **BNB Chain** was the third candidate (cheap, EVM, Binance rails) and stays the respectable alternate.
- Built: `wbc/settlement.py` + `anchor_demo.py`. Devnet project wallet: AmZXSCXvnM1ZwGq3AxGEpmWh838bwhMCCSBkgcC8zSgU (test keypair, no real funds). Gate as of Nov 23, 2026: Solana closed the public RPC faucet — devnet SOL comes from faucet.solana.com (GitHub sign-in, a founder tap); once funded, the anchor run fires and verifies each memo by read-back.

## The token and the bot (built Nov 23, 2026)
- **The token exists** (Solana devnet): mint `Btmsp8ASZkmt9uBkGs7AeL47xQUeDuAozt7hwC6cooqU`, 4 decimals (preserves exact ledger amounts), mint authority = project devnet wallet. The demo chain's writers were paid their exact earnings in it (Mara Venn 52.3847, Deke Pryor 25.0323, Wren 22.583 — balances verified on-chain). The coin's name/symbol metadata waits for the founder to coin the name.
- **The Writer Prompt Bot** (`writer_bot.py`) is the encouragement engine: it offers a writing prompt, counts the writer's strokes as they write, enters the piece into the pool, and when a block seals it stamps the block on Solana and mints each writer's share into their wallet, then shows the published ledger. Verified end-to-end Nov 23, 2026: two writers, two blocks sealed and anchored (read-back verified), 50 tokens each, chain valid, 1,081 strokes mined.

## The build ladder
1. **v0 — engine (DONE)**: single-node chain, proof-of-stroke, rewards, published-writers ledger, JSON persistence, tamper verification.
2. **v1 — the writing room**: a web page where a writer types and watches strokes count live, blocks seal, and their name land in the published ledger. This is the demo anyone can touch.
3. **v2 — pen strokes**: a drawing/writing canvas that counts pen strokes alongside keystrokes — the mechanism stops caring how the stroke was made.
4. **v3 — wallets and the coin**: writers hold keys; earnings become balances they control. **The coin's name is the founder's to coin** (v0 calls them "stroke credits" as a placeholder only).
5. **v4 — the network**: multiple nodes, writers mining from anywhere, the ledger public.

## Honest limits (v0)
- Single node: one machine holds the chain. It proves the mechanism; it is not yet a network and its units are not money.
- Stroke honesty: v0 counts characters in submitted text — pasted text counts the same as typed. The v1 writing room counts *live* keystrokes, which is where proof-of-stroke gets its teeth (pacing, rhythm, revision patterns are hard to fake at scale).
- Nothing here is publicly disclosed. The code stays in Pensativity Solutions' private workspace until the founder decides the trademark/patent posture — disclosure starts clocks.

## Files
- `wbc/chain.py` — the engine (blocks, proof-of-stroke, rewards, publishing, verification).
- `demo.py` — the demonstration run (three writers from the founder's own universe, as seed content).
- `demo-chain.json` — the demo chain, written by the run.
