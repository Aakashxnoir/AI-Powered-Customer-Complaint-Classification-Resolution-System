"""Duplicate detection on normalised sentence embeddings.

Each complaint carries identity keys: its order IDs and its customer ID (if known).
Two complaints are likely duplicates when:
  - they share an identity key and similarity >= SAME_ORDER_SIM, or
  - identity is unknown on at least one side and similarity >= SIM_THRESHOLD.
Complaints about different order IDs, or with identity keys but none in common,
are never duplicates:
different customers often describe the same problem in near-identical words, but
they are separate cases. Those are surfaced as "similar complaints" and in Trends.
"""
import numpy as np

SIM_THRESHOLD = 0.88
SAME_ORDER_SIM = 0.8  # chosen from the threshold sweep in ml/evaluate.py


def is_duplicate(sim: float, keys_a: set, keys_b: set) -> bool:
    orders_a = {k for k in keys_a if not k.startswith("cust:")}
    orders_b = {k for k in keys_b if not k.startswith("cust:")}
    if orders_a and orders_b and not orders_a & orders_b:
        return False  # explicitly about different orders
    if keys_a & keys_b:
        return sim >= SAME_ORDER_SIM
    if keys_a and keys_b:
        return False
    return sim >= SIM_THRESHOLD


def find_match(vec: np.ndarray, keys: set, pool_vecs: np.ndarray, pool_keys: list[set]):
    """Return (index, similarity) of the best duplicate in the pool, or None."""
    if len(pool_vecs) == 0:
        return None
    sims = pool_vecs @ vec
    for i in np.argsort(-sims)[:20]:
        if is_duplicate(float(sims[i]), keys, pool_keys[i]):
            return int(i), float(sims[i])
    return None


def identity_keys(entities: dict, customer: str | None) -> set:
    return set(entities.get("order_ids", [])) | ({f"cust:{customer.strip().lower()}"} if customer else set())


def similar(vec: np.ndarray, pool_vecs: np.ndarray, k: int = 5, min_sim: float = 0.5):
    """Top-k semantically similar complaints regardless of customer: [(index, similarity)]."""
    sims = pool_vecs @ vec
    return [(int(i), float(sims[i])) for i in np.argsort(-sims)[:k] if sims[i] >= min_sim]
