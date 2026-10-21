#!/usr/bin/env python3
"""Poll GitHub Actions for the latest run of a public repository."""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

API = "https://api.github.com"


def get(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "uefi-port-watch",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="HK416AAA/Phoenix_uefi_try")
    parser.add_argument("--workflow", default=None,
                        help="workflow file name, for example build-stub.yml")
    parser.add_argument("--interval", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    started = time.time()
    announced = False

    while True:
        try:
            data = get(f"{API}/repos/{args.repo}/actions/runs?per_page=10")
        except urllib.error.HTTPError as error:
            print(f"HTTP {error.code}: {error.reason}")
            return 2
        except urllib.error.URLError as error:
            print(f"network error: {error.reason}")
            return 2

        runs = data.get("workflow_runs", [])
        if args.workflow:
            runs = [
                run for run in runs
                if run.get("path", "").endswith(args.workflow)
                or run.get("name") == args.workflow
            ]

        if not runs:
            print("no workflow runs yet")
            if args.once:
                return 3
        else:
            run = runs[0]
            if not announced:
                announced = True
                print(f"watching #{run['run_number']} {run['name']} ({run['status']})")
                print(run["html_url"])

            line = f"{datetime.now().strftime('%H:%M:%S')}  #{run['run_number']}  {run['status']}"
            if run.get("conclusion"):
                line += f" / {run['conclusion']}"
            print(line, flush=True)

            if run["status"] == "completed":
                print(f"conclusion : {run.get('conclusion')}")
                print(f"run url    : {run['html_url']}")
                try:
                    artifacts = get(
                        f"{API}/repos/{args.repo}/actions/runs/{run['id']}/artifacts"
                    )
                    items = artifacts.get("artifacts", [])
                    if not items:
                        print("artifacts  : none")
                    for item in items:
                        print(f"artifact   : {item['name']} ({item['size_in_bytes']} bytes)")
                except urllib.error.HTTPError as error:
                    print(f"artifacts  : HTTP {error.code}; download from the web UI")
                return 0 if run.get("conclusion") == "success" else 1

        if args.once:
            return 0
        if time.time() - started > args.timeout:
            print("timeout waiting for a completed run")
            return 4
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
