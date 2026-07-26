"""Preflight check: confirms Cloudflare credentials work and the D1 schema
is initialized. Run this right after setting up .env, before running any
agent.

Usage: python3 verify_setup.py
"""

import logging
import sys

import requests

import storage


def _check(label: str, fn) -> bool:
    try:
        fn()
        print(f"  [OK]   {label}")
        return True
    except storage.R2NotEnabledError as exc:
        print(f"  [SKIP] {label}: {exc} (not blocking — R2 isn't needed yet)")
        return True
    except Exception as exc:
        print(f"  [FAIL] {label}: {exc}")
        return False


def _r2_reachable() -> None:
    if not storage.R2_BUCKET_NAME:
        raise storage.R2NotEnabledError("CLOUDFLARE_R2_BUCKET_NAME not set")
    try:
        storage.get_file("__verify_setup_probe__")
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return  # bucket is reachable; the probe object just doesn't exist
        raise


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print(f"Account: {storage.ACCOUNT_ID}")
    print(f"D1 database: {storage.D1_DATABASE_ID}")
    print(f"Vectorize index: {storage.VECTORIZE_INDEX_NAME}")
    print(f"R2 bucket: {storage.R2_BUCKET_NAME or '(not configured)'}")
    print()
    print("Running checks...")

    results = [
        _check("Cloudflare API token valid + D1 schema initialized", storage.init_db),
        _check("Vectorize index reachable", lambda: storage.list_kb_ids(limit=1)),
        _check("Workers AI embedding model reachable", lambda: storage._embed(["setup check"])),
        _check("R2 bucket reachable", _r2_reachable),
    ]

    print()
    if all(results):
        print("Setup looks good — ready to run agents.")
        return 0
    print("One or more checks failed — see above before running any agent.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
