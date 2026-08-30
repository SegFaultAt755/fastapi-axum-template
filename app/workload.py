import hashlib

DEFAULT_ITERATIONS = 2_000
MAX_ITERATIONS = 100_000


def compute_digest(data: str, iterations: int) -> str:
    payload = data.encode("utf-8")
    digest = payload
    for _ in range(iterations):
        digest = hashlib.sha256(digest + payload).digest()
    return digest.hex()