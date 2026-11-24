"""
Writer's Block Blockchain — the token (v0, Solana devnet)
Copyright (c) 2026 Pensativity Solutions LLC. All rights reserved.

Creates the WBC token as an SPL mint on Solana devnet and pays writers
their chain-earned rewards in it. The mint authority is the project
devnet wallet. The coin's NAME is still the founder's to coin — on-chain
metadata naming happens at his word; this module builds the money itself.

Devnet only: these tokens are test instruments, not money.
"""

import json
import os
import struct
import time

from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.message import Message
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from .settlement import _hash_from_string, rpc

TOKEN_PROGRAM = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ATA_PROGRAM = Pubkey.from_string("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL")
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")
RENT_SYSVAR = Pubkey.from_string("SysvarRent111111111111111111111111111111111")
DEVNET_URL = "https://api.devnet.solana.com"
DECIMALS = 4  # preserves the ledger's exact reward amounts (e.g. 52.3847)
MINT_SPACE = 82
ACCOUNT_SPACE = 165

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN_RECORD = os.path.join(HERE, "..", "token-record.json")


def send_tx(url, instructions, payer: Keypair, extra_signers=()):
    bh = rpc(url, "getLatestBlockhash",
             [{"commitment": "finalized"}])["value"]["blockhash"]
    blockhash = _hash_from_string(bh)
    msg = Message.new_with_blockhash(instructions, payer.pubkey(), blockhash)
    txn = Transaction([payer, *extra_signers], msg, blockhash)
    import base64
    wire = base64.b64encode(bytes(txn)).decode()
    sig = rpc(url, "sendTransaction", [wire, {"encoding": "base64",
                                              "maxRetries": 5}])
    for _ in range(40):
        res = rpc(url, "getSignatureStatuses", [[sig]])
        status = res["value"][0]
        if status and status.get("confirmationStatus") in ("confirmed",
                                                           "finalized"):
            if status.get("err"):
                raise RuntimeError(f"tx failed on-chain: {status['err']}")
            return sig
        time.sleep(3)
    raise RuntimeError(f"tx {sig} not confirmed in time")


def _create_account_ix(payer, new_account, space, owner, lamports):
    data = struct.pack("<I", 0) + struct.pack("<q", lamports) + \
        struct.pack("<Q", space) + bytes(owner)
    return Instruction(SYSTEM_PROGRAM, data, [
        AccountMeta(payer, True, True),
        AccountMeta(new_account, True, True),
    ])


def _initialize_mint_ix(mint, decimals, authority):
    data = bytes([0, decimals]) + bytes(authority) + bytes([0])
    return Instruction(TOKEN_PROGRAM, data, [
        AccountMeta(mint, False, True),
        AccountMeta(RENT_SYSVAR, False, False),
    ])


def ata_address(wallet, mint):
    return Pubkey.find_program_address(
        [bytes(wallet), bytes(TOKEN_PROGRAM), bytes(mint)], ATA_PROGRAM)[0]


def _create_ata_ix(payer, wallet, mint):
    ata = ata_address(wallet, mint)
    return Instruction(ATA_PROGRAM, bytes([1]), [  # 1 = CreateIdempotent
        AccountMeta(payer, True, True),
        AccountMeta(ata, False, True),
        AccountMeta(wallet, False, False),
        AccountMeta(mint, False, False),
        AccountMeta(SYSTEM_PROGRAM, False, False),
        AccountMeta(TOKEN_PROGRAM, False, False),
    ]), ata


def _mint_to_ix(mint, destination, authority, amount_units):
    data = bytes([7]) + struct.pack("<Q", amount_units)
    return Instruction(TOKEN_PROGRAM, data, [
        AccountMeta(mint, False, True),
        AccountMeta(destination, False, True),
        AccountMeta(authority, True, False),
    ])


class WbcToken:
    def __init__(self, payer: Keypair, url=DEVNET_URL):
        self.payer = payer
        self.url = url
        self.mint = None
        if os.path.exists(TOKEN_RECORD):
            with open(TOKEN_RECORD) as f:
                self.mint = Pubkey.from_string(json.load(f)["mint"])

    def create_mint(self):
        mint_kp = Keypair()
        rent = rpc(self.url, "getMinimumBalanceForRentExemption",
                   [MINT_SPACE])
        sig = send_tx(self.url, [
            _create_account_ix(self.payer.pubkey(), mint_kp.pubkey(),
                               MINT_SPACE, TOKEN_PROGRAM, rent),
            _initialize_mint_ix(mint_kp.pubkey(), DECIMALS,
                                self.payer.pubkey()),
        ], self.payer, extra_signers=[mint_kp])
        self.mint = mint_kp.pubkey()
        self._save_record(sig)
        return str(self.mint), sig

    def pay_writer(self, wallet: Pubkey, earned: float):
        """Mint a writer's earned rewards into their wallet."""
        units = int(round(earned * (10 ** DECIMALS)))
        create_ix, ata = _create_ata_ix(self.payer.pubkey(), wallet, self.mint)
        sig = send_tx(self.url, [
            create_ix,
            _mint_to_ix(self.mint, ata, self.payer.pubkey(), units),
        ], self.payer)
        return str(ata), sig

    def balance(self, wallet: Pubkey):
        ata = ata_address(wallet, self.mint)
        res = rpc(self.url, "getTokenAccountBalance", [str(ata)])
        return res["value"]["uiAmountString"]

    def _save_record(self, sig):
        with open(TOKEN_RECORD, "w") as f:
            json.dump({
                "network": "solana-devnet",
                "mint": str(self.mint),
                "decimals": DECIMALS,
                "mint_authority": str(self.payer.pubkey()),
                "created_in_tx": sig,
                "note": "Test instrument on devnet. The coin's name is the "
                        "founder's to coin; on-chain naming follows his word.",
            }, f, indent=1)


def load_or_create_writer_wallets(names, path):
    wallets = {}
    if os.path.exists(path):
        with open(path) as f:
            stored = json.load(f)
        for name, secret in stored["wallets"].items():
            wallets[name] = Keypair.from_bytes(bytes(secret))
    changed = False
    for name in names:
        if name not in wallets:
            wallets[name] = Keypair()
            changed = True
    if changed or not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({
                "warning": "DEVNET writer wallets — test keys, no real funds",
                "wallets": {n: list(bytes(kp)) for n, kp in wallets.items()},
            }, f, indent=1)
    return wallets
