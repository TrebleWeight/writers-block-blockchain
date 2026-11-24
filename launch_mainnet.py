"""
Writer's Block Blockchain — MAINNET launch (founder-gated)
Copyright (c) 2026 Pensativity Solutions LLC. All rights reserved.

Creates the real WBC token on Solana MAINNET from the mainnet project
wallet (mainnet-keypair.json). No pre-mine: supply begins at zero and
coins come into existence only as block rewards, exactly as designed.
The mint authority stays with the project wallet so sealed blocks can
pay their writers.

Run only on the founder's explicit order, after he funds the wallet:
  /tmp/wbcvenv/bin/python launch_mainnet.py --name "<coin name>" --symbol "<SYM>"

Without --name/--symbol it creates the mint unnamed (naming can follow;
the metadata account is updatable while the founder holds authority).
"""

import argparse
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from solders.instruction import AccountMeta, Instruction  # noqa: E402
from solders.keypair import Keypair  # noqa: E402
from solders.pubkey import Pubkey  # noqa: E402

from wbc.settlement import rpc  # noqa: E402
from wbc.token import (DECIMALS, MINT_SPACE, RENT_SYSVAR, SYSTEM_PROGRAM,  # noqa: E402
                       TOKEN_PROGRAM, _create_account_ix, _initialize_mint_ix,
                       send_tx)

HERE = os.path.dirname(os.path.abspath(__file__))
MAINNET_URL = "https://api.mainnet-beta.solana.com"
RECORD = os.path.join(HERE, "mainnet-token-record.json")
METADATA_PROGRAM = Pubkey.from_string(
    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
MIN_LAUNCH_LAMPORTS = 8_000_000  # covers mint + metadata + ATAs + fees


def _borsh_string(s):
    b = s.encode("utf-8")
    return struct.pack("<I", len(b)) + b


def metadata_ix(mint, authority, name, symbol, uri=""):
    metadata = Pubkey.find_program_address(
        [b"metadata", bytes(METADATA_PROGRAM), bytes(mint)],
        METADATA_PROGRAM)[0]
    data = bytes([33])  # CreateMetadataAccountV3
    data += _borsh_string(name) + _borsh_string(symbol) + _borsh_string(uri)
    data += struct.pack("<H", 0)      # seller_fee_basis_points
    data += bytes([0, 0, 0])          # creators, collection, uses: none
    data += bytes([1])                # is_mutable
    data += bytes([0])                # collection_details: none
    ix = Instruction(METADATA_PROGRAM, data, [
        AccountMeta(metadata, False, True),
        AccountMeta(mint, False, False),
        AccountMeta(authority, True, False),
        AccountMeta(authority, True, True),
        AccountMeta(authority, False, False),  # update authority
        AccountMeta(SYSTEM_PROGRAM, False, False),
        AccountMeta(RENT_SYSVAR, False, False),
    ])
    return ix, metadata


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default=None)
    ap.add_argument("--symbol", default=None)
    args = ap.parse_args()

    payer = Keypair.from_bytes(
        bytes(json.load(open(os.path.join(HERE, "mainnet-keypair.json")))
              ["secret"]))
    balance = rpc(MAINNET_URL, "getBalance", [str(payer.pubkey())])["value"]
    print(f"Mainnet launch wallet: {payer.pubkey()}")
    print(f"Balance: {balance / 1e9} SOL")
    if balance < MIN_LAUNCH_LAMPORTS:
        print(f"NOT FUNDED ENOUGH: launch needs at least "
              f"{MIN_LAUNCH_LAMPORTS / 1e9} SOL in the wallet.")
        return

    if os.path.exists(RECORD):
        rec = json.load(open(RECORD))
        print(f"Mint already created: {rec['mint']}")
        return

    mint_kp = Keypair()
    rent = rpc(MAINNET_URL, "getMinimumBalanceForRentExemption",
               [MINT_SPACE])
    sig = send_tx(MAINNET_URL, [
        _create_account_ix(payer.pubkey(), mint_kp.pubkey(), MINT_SPACE,
                           TOKEN_PROGRAM, rent),
        _initialize_mint_ix(mint_kp.pubkey(), DECIMALS, payer.pubkey()),
    ], payer, extra_signers=[mint_kp])
    mint = mint_kp.pubkey()
    print(f"MAINNET MINT CREATED: {mint} (tx {sig})")

    record = {"network": "solana-mainnet", "mint": str(mint),
              "decimals": DECIMALS, "mint_authority": str(payer.pubkey()),
              "created_in_tx": sig, "name": args.name,
              "symbol": args.symbol, "supply_at_launch": 0,
              "note": "No pre-mine. Supply is born as block rewards."}

    if args.name and args.symbol:
        ix, metadata = metadata_ix(mint, payer.pubkey(), args.name,
                                   args.symbol)
        msig = send_tx(MAINNET_URL, [ix], payer)
        record["metadata_account"] = str(metadata)
        record["metadata_tx"] = msig
        print(f"Named on-chain: {args.name} ({args.symbol}) — tx {msig}")
    else:
        print("Mint created UNNAMED — the founder coins the name, then "
              "metadata is written.")

    with open(RECORD, "w") as f:
        json.dump(record, f, indent=1)
    print("Record saved:", RECORD)
    print("Explorer: https://explorer.solana.com/address/" + str(mint))


if __name__ == "__main__":
    main()
