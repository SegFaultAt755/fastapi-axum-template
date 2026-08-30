# FastAPI & Axum Benchmark

A performance test between **FastAPI** and **Axum**. Both hit the same Postgres database and expose identical endpoints to test throughput, latency, and resource usage.

---

## Requirements

* **Docker & Docker Compose**
* **`wrk`** (for load testing):
    * Mac: `brew install wrk`
    * Linux: `sudo apt-get install wrk`

---

## Quick Start

### Spin everything up

```bash
docker compose up -d
docker compose exec api python generate.py 100000
```

*(This starts Postgres with 100k generated test users, FastAPI on port 8000, and Axum on port 8001).*

### Verify they're alive

```bash
curl http://127.0.0.1:8000/  # FastAPI
curl http://127.0.0.1:8001/  # Axum
```

### Run the benchmarks

```bash
# Test FastAPI with defaults (30s, 2 threads, 100 connections)
./benchmark.sh

# Test both frameworks back-to-back
./benchmark-both.sh

# Custom settings
BASE_URL=http://127.0.0.1:8001 DURATION=60s THREADS=4 CONNECTIONS=200 ./benchmark.sh
```

---

## The Endpoints

| Method | Endpoint | What it does |
| --- | --- | --- |
| GET | `/` | Basic health check (minimal load) |
| GET | `/user/{id}` | DB read: Fetch user by ID |
| GET | `/compute` | CPU test: SHA256 hashing |
| GET | `/compute_db` | Combo test: DB lookup + SHA256 hash |
| PUT | `/update/{id}` | DB write: Update a user's age |

---

## Checking the Results

Once benchmark finishes, head to the `benchmark/results/{framework}/{timestamp}/` folder. You'll find a text file for each endpoint (e.g., `user.txt`, `compute.txt`) containing the `wrk` output, including requests-per-second and latency percentiles.

---

## Teardown

When you're done breaking things, wipe the containers and the database volume:

```bash
docker compose down -v
```
