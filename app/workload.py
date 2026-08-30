"""CPU-bound hashing helpers used by the benchmark endpoints."""

import hashlib

DEFAULT_ITERATIONS = 2_000
MAX_ITERATIONS = 100_000


def _hash_round(digest: bytes, payload: bytes) -> bytes:
    """Perform one SHA-256 round for the benchmark workload."""
    return hashlib.sha256(digest + payload).digest()


def compute_digest(data: str, iterations: int) -> str:
    """Repeat the hash chain to create a deterministic, CPU-heavy workload.

    The benchmark intentionally reuses the previous digest and the original payload on
    each pass so the total work grows linearly with the requested iteration count.
    """
    if iterations < 1:
        raise ValueError("iterations must be at least 1")

    payload = data.encode("utf-8")
    digest = payload
    for _ in range(iterations):
        digest = _hash_round(digest, payload)
    return digest.hex()
