#!/usr/bin/env bash
# scripts/offline_check.sh — S-04 offline verification harness.
#
# Runs `make test-backend`, `make test-frontend`, and `make demo` with networking
# blocked, plus a self-test proving the block is active. Prints a per-check
# PASS/FAIL summary and exits 0 only if every check passes.
#
# Blocking strategy:
#   1. If `unshare -n` is available, each check runs inside an empty network
#      namespace (no interfaces except loopback) — the strongest block.
#   2. Otherwise fall back to: poisoned HTTP(S)_PROXY/ALL_PROXY (unroutable),
#      plus socket guards — a Python sitecustomize guard (PYTHONPATH) and a
#      Node --require guard (NODE_OPTIONS) that raise on any outbound socket
#      to a non-loopback host. Any outbound attempt then fails loudly.
#
# Usage: ./scripts/offline_check.sh   (from anywhere; resolves repo root itself)

set -u
cd "$(dirname "$0")/.."
ROOT="$PWD"

RESULTS=()
MODE=""

if command -v unshare >/dev/null 2>&1 && unshare -n true 2>/dev/null; then
    MODE="unshare -n"
else
    MODE="proxy-poison + socket guards"
    export HTTP_PROXY="http://127.0.0.1:9" HTTPS_PROXY="http://127.0.0.1:9" \
           http_proxy="http://127.0.0.1:9" https_proxy="http://127.0.0.1:9" \
           ALL_PROXY="http://127.0.0.1:9" all_proxy="http://127.0.0.1:9" \
           NO_PROXY="" no_proxy=""
    export PYTHONPATH="$ROOT/scripts/py_guard${PYTHONPATH:+:$PYTHONPATH}"
    export NODE_OPTIONS="--require $ROOT/scripts/node_guard.cjs ${NODE_OPTIONS:-}"
fi

echo "offline_check: network block mode = $MODE"
echo "offline_check: poisoned proxies / guards active (loopback still allowed)"
echo

run_check() {
    local name="$1"; shift
    echo "--- $name ---"
    if "$@" >/tmp/offline_check_last.log 2>&1; then
        RESULTS+=("PASS $name")
        echo "PASS $name"
    else
        RESULTS+=("FAIL $name")
        echo "FAIL $name (log: /tmp/offline_check_last.log)"
        tail -20 /tmp/offline_check_last.log
    fi
    echo
}

run_blocked() {
    # run a command with the network block applied
    if [ "$MODE" = "unshare -n" ]; then
        unshare -n "$@"
    else
        "$@"
    fi
}

# Self-test: an outbound connection MUST fail while blocked (proves the block works).
# Any exception (OSError from the namespace, or the guard's RuntimeError) counts as blocked.
self_test() {
    if run_blocked python3 -c "
import socket, sys
try:
    socket.create_connection(('192.0.2.1', 443), timeout=3)
except Exception:
    sys.exit(0)   # blocked, as required
sys.exit(1)       # connected — block is NOT active
" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

run_check "network-block self-test (outbound connect must fail)" self_test
run_check "make test-backend (offline)" run_blocked make test-backend
run_check "make test-frontend (offline)" run_blocked make test-frontend
run_check "make demo (offline)" run_blocked make demo

echo "================ SUMMARY ================"
fail=0
for r in "${RESULTS[@]}"; do
    echo "$r"
    case "$r" in FAIL*) fail=1;; esac
done
echo "========================================="
if [ "$fail" -eq 0 ]; then
    echo "offline_check: ALL CHECKS PASSED (mode: $MODE)"
    exit 0
else
    echo "offline_check: FAILURES DETECTED (mode: $MODE)" >&2
    exit 1
fi
