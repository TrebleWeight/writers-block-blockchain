// WBB pool status — read-only. Run: node pool_status.js
const { Connection, PublicKey } = require("@solana/web3.js");
const { getAccount } = require("@solana/spl-token");
const sdk = require("@meteora-ag/cp-amm-sdk");
const POOL = new PublicKey("2xTNGius4AoooT5uwydtooDuPukLWrhmpjRtJcz5FoBW");
const WBB = new PublicKey("HqUfKmTZz5199C975hEwG6yGNXdaJVSuThgBFGu4a5Gs");
const WSOL = new PublicKey("So11111111111111111111111111111111111111112");
(async () => {
  const conn = new Connection("https://api.mainnet-beta.solana.com", "confirmed");
  const va = await getAccount(conn, sdk.deriveTokenVaultAddress(WBB, POOL));
  const vb = await getAccount(conn, sdk.deriveTokenVaultAddress(WSOL, POOL));
  const wbb = Number(va.amount) / 1e4, sol = Number(vb.amount) / 1e9;
  console.log("pool:", POOL.toBase58());
  console.log("reserves:", wbb.toFixed(4), "WBB |", sol.toFixed(6), "SOL");
  console.log("spot price:", (sol / wbb).toFixed(6), "SOL per WBB");
  const supply = await conn.getTokenSupply(WBB);
  console.log("WBB supply:", supply.value.uiAmountString);
})().catch(e => { console.error("ERR", e.message); process.exit(1); });
