#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
DURATION="${DURATION:-30s}"
THREADS="${THREADS:-6}"
CONNECTIONS="${CONNECTIONS:-100}"
USER_COUNT="${USER_COUNT:-100000}"
WARMUP_REQUESTS="${WARMUP_REQUESTS:-100}"
RESULTS_DIR="${RESULTS_DIR:-benchmark/results}"

command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }
command -v wrk >/dev/null || { echo "wrk is required" >&2; exit 1; }

if ! [[ "$USER_COUNT" =~ ^[1-9][0-9]*$ ]]; then
    echo "USER_COUNT must be a positive integer" >&2
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
EOF

echo "Waiting for $BASE_URL ..."
curl --fail --silent --show-error --retry 30 --retry-delay 1 --retry-connrefused \
    "$BASE_URL/" >/dev/null

echo "Warming up with $WARMUP_REQUESTS requests ..."
for ((request_number = 1; request_number <= WARMUP_REQUESTS; request_number++)); do
    curl --fail --silent --show-error -H 'Cache-Control: no-cache' \
        "$BASE_URL/" >/dev/null
done

echo "Benchmarking root route ..."
wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" \
    -s "$SCRIPT_DIR/benchmark/root.lua" "$BASE_URL/" \
    >"$run_dir/root.txt" 2>&1

echo "Benchmarking random user route ..."
USER_COUNT="$USER_COUNT" wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" \
    -s "$SCRIPT_DIR/benchmark/user.lua" "$BASE_URL" \
    >"$run_dir/user.txt" 2>&1

printf 'Results saved in %s\n' "$run_dir"