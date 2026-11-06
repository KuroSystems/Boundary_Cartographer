"""Offline terminal demo — `python -m app.demo --print` (S-04 placeholder).

The full 8-step demo transcript lands with BE-11/INT-01; this stub keeps
`make demo` (and scripts/offline_check.sh) runnable and offline-safe from S-04 on.
"""

import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.demo")
    parser.add_argument("--print", action="store_true", help="print the demo transcript as JSON")
    parser.parse_args()

    transcript = {
        "demo": "boundary-cartographer",
        "mode": "offline",
        "note": "placeholder transcript — full 8-step demo lands with BE-11/INT-01",
        "steps": [],
    }
    print(json.dumps(transcript, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
