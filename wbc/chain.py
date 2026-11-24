"""
Writer's Block Blockchain — core engine (v0 prototype)
Copyright (c) 2026 Pensativity Solutions LLC. All rights reserved.

The mechanism, in Anthony Wilkerson's words: a blockchain that mines crypto
by counting strokes, and encourages and publishes its miners — the writers.

CONSENSUS: Proof-of-Stroke.
  - A "stroke" is one keystroke that produces a character (letters,
    punctuation, spaces). Pen-stroke input can feed the same counter later;
    the engine counts stroke EVENTS, whatever the source. Strokes are the
    proof the writing happened; words are the measure of the block.
  - Writers submit writing in segments. Each segment's strokes and words
    are counted and held in the pending pool, credited to its writer.
  - When the pool's total words reach BLOCK_WORD_THRESHOLD (1,000 words),
    the next block seals: it binds every pending segment (writer, title,
    text, its hash) into the chain under one block hash linked to the
    previous block.
  - BLOCK_REWARD units are minted by the seal and split among the block's
    writers in proportion to the words each contributed. Writing is the
    work; the work is the mining.
  - The chain PUBLISHES its writers: a public ledger of who wrote, what
    they published, how many strokes and words, and what they earned.

Founder's change, Nov 23, 2026: the block unit is 1,000 WORDS per block,
superseding the v0 500-stroke seal. Strokes are still counted on every
segment as the proof-of-writing; words size and seal the block.

This is a working prototype of the mechanism — a single-node chain with
JSON persistence. It is not yet a network, and its units are not money.
"""

import hashlib
import json
import os
import time

BLOCK_WORD_THRESHOLD = 1000    # words of writing required to seal a block
BLOCK_REWARD = 50.0            # units minted per sealed block, split by words
UNIT = "stroke credits"        # placeholder name — the coin's name is the founder's to coin


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_strokes(text: str) -> int:
    """One stroke per character produced. Every keystroke counts."""
    return len(text)


def count_words(text: str) -> int:
    """One word per whitespace-separated token."""
    return len(text.split())


class Segment:
    """One piece of writing submitted by one writer."""

    def __init__(self, writer: str, title: str, text: str):
        self.writer = writer
        self.title = title
        self.text = text
        self.strokes = count_strokes(text)
        self.words = count_words(text)
        self.hash = sha256(writer + "|" + title + "|" + text)

    def to_dict(self):
        return {
            "writer": self.writer,
            "title": self.title,
            "text": self.text,
            "strokes": self.strokes,
            "words": self.words,
            "hash": self.hash,
        }

    @staticmethod
    def from_dict(d):
        s = Segment(d["writer"], d["title"], d["text"])
        assert s.hash == d["hash"] and s.strokes == d["strokes"]
        return s


class Block:
    def __init__(self, index, previous_hash, segments, timestamp=None):
        self.index = index
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.previous_hash = previous_hash
        self.segments = segments  # list[Segment]
        self.total_strokes = sum(s.strokes for s in segments)
        self.total_words = sum(s.words for s in segments)
        self.rewards = self._split_rewards()
        self.hash = self._compute_hash()

    def _split_rewards(self):
        if self.total_words == 0:
            return {}
        rewards = {}
        for s in self.segments:
            share = BLOCK_REWARD * s.words / self.total_words
            rewards[s.writer] = round(rewards.get(s.writer, 0.0) + share, 4)
        return rewards

    def _payload(self):
        return "|".join([
            str(self.index),
            str(self.timestamp),
            self.previous_hash,
            ";".join(s.hash for s in self.segments),
            str(self.total_strokes),
            str(self.total_words),
        ])

    def _compute_hash(self):
        return sha256(self._payload())

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "segments": [s.to_dict() for s in self.segments],
            "total_strokes": self.total_strokes,
            "total_words": self.total_words,
            "rewards": self.rewards,
            "hash": self.hash,
        }

    @staticmethod
    def from_dict(d):
        segments = [Segment.from_dict(s) for s in d["segments"]]
        b = Block(d["index"], d["previous_hash"], segments, d["timestamp"])
        assert b.hash == d["hash"], "block hash mismatch — chain data altered"
        return b


class WritersBlockChain:
    def __init__(self, store_path=None):
        self.store_path = store_path
        self.blocks = []
        self.pending = []  # list[Segment] not yet sealed
        if store_path and os.path.exists(store_path):
            self._load()
        if not self.blocks:
            genesis = Block(0, "0" * 64, [], timestamp=0)
            self.blocks = [genesis]

    # --- writing / mining -------------------------------------------------
    def submit_writing(self, writer: str, title: str, text: str):
        """A writer writes. Strokes and words are counted immediately; if
        the pool crosses 1,000 words, the block seals and rewards are paid."""
        seg = Segment(writer, title, text)
        self.pending.append(seg)
        sealed = None
        if sum(s.words for s in self.pending) >= BLOCK_WORD_THRESHOLD:
            sealed = self._seal_block()
        self._save()
        return seg, sealed

    def _seal_block(self):
        block = Block(len(self.blocks), self.blocks[-1].hash, self.pending)
        self.blocks.append(block)
        self.pending = []
        return block

    # --- publishing -------------------------------------------------------
    def published_writers(self):
        """The chain publishes its miners: every writer, their works,
        their lifetime strokes and words, and their lifetime earnings."""
        writers = {}
        for block in self.blocks[1:]:
            for s in block.segments:
                w = writers.setdefault(s.writer, {
                    "writer": s.writer, "works": [], "strokes": 0,
                    "words": 0, "earned": 0.0,
                })
                w["works"].append({"title": s.title, "strokes": s.strokes,
                                   "words": s.words, "block": block.index})
                w["strokes"] += s.strokes
                w["words"] += s.words
            for writer, amount in block.rewards.items():
                writers[writer]["earned"] = round(
                    writers[writer]["earned"] + amount, 4)
        return sorted(writers.values(), key=lambda w: -w["words"])

    # --- integrity --------------------------------------------------------
    def verify(self):
        for i, block in enumerate(self.blocks):
            if block._compute_hash() != block.hash:
                return False, f"block {i}: hash does not recompute"
            if i > 0 and block.previous_hash != self.blocks[i - 1].hash:
                return False, f"block {i}: previous-hash link broken"
            for s in block.segments:
                if Segment(s.writer, s.title, s.text).hash != s.hash:
                    return False, f"block {i}: segment altered"
        return True, f"chain valid — {len(self.blocks)} blocks, " \
                     f"{sum(b.total_words for b in self.blocks)} words mined " \
                     f"({sum(b.total_strokes for b in self.blocks)} strokes)"

    # --- persistence ------------------------------------------------------
    def _save(self):
        if not self.store_path:
            return
        data = {
            "blocks": [b.to_dict() for b in self.blocks],
            "pending": [s.to_dict() for s in self.pending],
        }
        with open(self.store_path, "w") as f:
            json.dump(data, f, indent=1)

    def _load(self):
        with open(self.store_path) as f:
            data = json.load(f)
        self.blocks = [Block.from_dict(d) for d in data["blocks"]]
        self.pending = [Segment.from_dict(d) for d in data["pending"]]
