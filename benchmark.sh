#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
DURATION="${DURATION:-30s}"
THREADS="${THREADS:-2}"
CONNECTIONS="${CONNECTIONS:-100}"
WARMUP_REQUESTS="${WARMUP_REQUESTS:-100}"
CPU_ITERATIONS="${CPU_ITERATIONS:-20000}"
RESULTS_DIR="${RESULTS_DIR:-benchmark/results}"

command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }
command -v wrk >/dev/null || { echo "wrk is required" >&2; exit 1; }

DB_USER_COUNT=""
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    DB_USER_COUNT=$(docker compose exec -T postgres psql -U app_user -d app_db -tAc 'SELECT COUNT(*) FROM users;' 2>/dev/null || true)
fi

if [[ -n "$DB_USER_COUNT" ]] && [[ "$DB_USER_COUNT" =~ ^[0-9]+$ ]]; then
    if [[ -z "${USER_COUNT:-}" ]]; then
        USER_COUNT="$DB_USER_COUNT"
    elif [[ "$USER_COUNT" -gt "$DB_USER_COUNT" ]]; then
        echo "USER_COUNT=$USER_COUNT exceeds database user count ($DB_USER_COUNT); benchmark would hit missing IDs" >&2
        exit 1
    fi
else
    USER_COUNT="${USER_COUNT:-100000}"
fi

if ! [[ "$USER_COUNT" =~ ^[1-9][0-9]*$ ]]; then
    echo "USER_COUNT must be a positive integer" >&2
    exit 1
fi

if ! [[ "$CPU_ITERATIONS" =~ ^[1-9][0-9]*$ ]] || ((CPU_ITERATIONS > 100000)); then
    echo "CPU_ITERATIONS must be between 1 and 100000" >&2
    exit 1
fi

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
run_dir="$RESULTS_DIR/$timestamp"
mkdir -p "$run_dir"

cat >"$run_dir/config.txt" <<EOF
base_url=$BASE_URL
duration=$DURATION
threads=$THREADS
connections=$CONNECTIONS
user_count=$USER_COUNT
warmup_requests=$WARMUP_REQUESTS
cpu_iterations=$CPU_ITERATIONS
EOF

echo "Waiting for $BASE_URL ..."
curl --fail --silent --show-error --retry 30 --retry-delay 1 --retry-connrefused \
    "$BASE_URL/" >/dev/null

echo "Checking live user route coverage for IDs 1..$USER_COUNT ..."
curl --fail --silent --show-error "$BASE_URL/user/1" >/dev/null
curl --fail --silent --show-error "$BASE_URL/user/$USER_COUNT" >/dev/null
curl --fail --silent --show-error "$BASE_URL/compute?iterations=$CPU_ITERATIONS&data=benchmark-payload" >/dev/null
curl --fail --silent --show-error "$BASE_URL/compute-db/1?iterations=$CPU_ITERATIONS" >/dev/null
curl --fail --silent --show-error -X PUT "$BASE_URL/user/1/age/30" >/dev/null

echo "Warming up all routes with $WARMUP_REQUESTS requests per route ..."
for ((request_number = 1; request_number <= WARMUP_REQUESTS; request_number++)); do
    curl --fail --silent --show-error -H 'Cache-Control: no-cache' \
        "$BASE_URL/" >/dev/null
    curl --fail --silent --show-error -H 'Cache-Control: no-cache' \
        "$BASE_URL/user/1" >/dev/null
    curl --fail --silent --show-error -H 'Cache-Control: no-cache' \
        "$BASE_URL/user/1/age/30" -X PUT >/dev/null
    curl --fail --silent --show-error -H 'Cache-Control: no-cache' \
        "$BASE_URL/compute?iterations=$CPU_ITERATIONS&data=benchmark-payload" >/dev/null
    curl --fail --silent --show-error -H 'Cache-Control: no-cache' \
        "$BASE_URL/compute-db/1?iterations=$CPU_ITERATIONS" >/dev/null
done

echo "Benchmarking root route ..."
wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" \
    -s "$SCRIPT_DIR/benchmark/root.lua" "$BASE_URL/" \
    >"$run_dir/root.txt" 2>&1

echo "Benchmarking random user route ..."
USER_COUNT="$USER_COUNT" wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" \
    -s "$SCRIPT_DIR/benchmark/user.lua" "$BASE_URL" \
    >"$run_dir/user.txt" 2>&1

echo "Benchmarking user age update route ..."
USER_COUNT="$USER_COUNT" wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" \
    -s "$SCRIPT_DIR/benchmark/update.lua" "$BASE_URL" \
    >"$run_dir/update.txt" 2>&1

echo "Benchmarking CPU route without database ..."
CPU_ITERATIONS="$CPU_ITERATIONS" wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" \
    -s "$SCRIPT_DIR/benchmark/compute.lua" "$BASE_URL" \
    >"$run_dir/compute.txt" 2>&1

echo "Benchmarking CPU route with database ..."
USER_COUNT="$USER_COUNT" CPU_ITERATIONS="$CPU_ITERATIONS" \
    wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" \
    -s "$SCRIPT_DIR/benchmark/compute_db.lua" "$BASE_URL" \
    >"$run_dir/compute_db.txt" 2>&1

printf 'Results saved in %s\n' "$run_dir"