
#!/usr/bin/env python3
"""
Codex App Server Remote Control Setup

Connect to an existing Codex App Server, enable Remote Control,
and complete manual pairing.

Dependencies:
    pip install "websockets>=13"

Usage:
    python codex_remote_setup.py

Environment:
    CODEX_APP_SERVER_URL=ws://127.0.0.1:4500
"""

import asyncio
import json
import os
import time
from datetime import datetime

from websockets.asyncio.client import connect


# ============================================================
# Configuration
# ============================================================

WS_URL = os.getenv(
    "CODEX_APP_SERVER_URL",
    "ws://127.0.0.1:4500",
)

CONNECT_TIMEOUT = 30
PAIRING_TIMEOUT = 180
POLL_INTERVAL = 3


# ============================================================
# JSON-RPC Client
# ============================================================

class CodexRPC:
    def __init__(self, websocket):
        self.ws = websocket
        self.next_id = 0

    async def request(self, method, params=None):
        self.next_id += 1
        request_id = self.next_id

        message = {
            "id": request_id,
            "method": method,
        }

        if params is not None:
            message["params"] = params

        await self.ws.send(json.dumps(message))

        while True:
            raw = await asyncio.wait_for(
                self.ws.recv(),
                timeout=CONNECT_TIMEOUT,
            )

            response = json.loads(raw)

            # Ignore notifications and responses with a different ID.
            if response.get("id") != request_id:
                continue

            if "error" in response:
                raise RuntimeError(
                    f"{method}: {response['error']}"
                )

            return response.get("result", {})

    async def notify(self, method, params=None):
        message = {
            "method": method,
        }

        if params is not None:
            message["params"] = params

        await self.ws.send(json.dumps(message))


# ============================================================
# Helpers
# ============================================================

def print_json(title, data):
    print(f"\n=== {title} ===")
    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )
    )


def format_expiration(timestamp):
    if timestamp is None:
        return "Unknown"

    try:
        return datetime.fromtimestamp(
            int(timestamp)
        ).astimezone().isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return str(timestamp)


# ============================================================
# Remote Control
# ============================================================

async def initialize(rpc):
    print("[1/5] Initializing App Server...")

    result = await rpc.request(
        "initialize",
        {
            "clientInfo": {
                "name": "python_remote_setup",
                "title": "Python Remote Setup",
                "version": "1.0.0",
            },
            "capabilities": {
                "experimentalApi": True,
            },
        },
    )

    await rpc.notify("initialized")

    print_json("Initialized", result)


async def enable_remote_control(rpc):
    print("\n[2/5] Enabling Remote Control...")

    result = await rpc.request(
        "remoteControl/enable",
        {
            "ephemeral": False,
        },
    )

    print_json("Remote Control Enable", result)

    return result


async def wait_for_connection(rpc):
    print("\n[3/5] Waiting for cloud connection...")

    deadline = time.monotonic() + CONNECT_TIMEOUT

    while time.monotonic() < deadline:
        result = await rpc.request(
            "remoteControl/status/read"
        )

        status = result.get("status")

        print(f"Remote status: {status}")

        if status == "connected":
            print("Remote Control connected.")
            return result

        if status == "errored":
            raise RuntimeError(
                f"Remote Control connection error: {result}"
            )

        await asyncio.sleep(2)

    raise TimeoutError(
        "Remote Control connection timed out."
    )


async def start_pairing(rpc):
    print("\n[4/5] Starting manual pairing...")

    pairing = await rpc.request(
        "remoteControl/pairing/start",
        {
            "manualCode": True,
        },
    )

    code = pairing.get("manualPairingCode")

    if not code:
        raise RuntimeError(
            "Manual pairing code was not returned."
        )

    print("\n" + "=" * 54)
    print("CODEX REMOTE CONTROL PAIRING")
    print("=" * 54)

    print(f"Manual pairing code : {code}")
    print(
        "Expires at          : "
        + format_expiration(pairing.get("expiresAt"))
    )
    print(
        "Environment ID      : "
        + str(pairing.get("environmentId"))
    )

    print("=" * 54)

    print(
        "\nEnter this pairing code on the ChatGPT Remote screen."
    )

    return pairing


async def wait_for_pairing(rpc, pairing):
    print("\n[5/5] Waiting for pairing confirmation...")

    code = pairing["manualPairingCode"]

    deadline = time.monotonic() + PAIRING_TIMEOUT

    while time.monotonic() < deadline:
        # pairingCode and manualPairingCode are mutually exclusive.
        result = await rpc.request(
            "remoteControl/pairing/status",
            {
                "manualPairingCode": code,
            },
        )

        if result.get("claimed") is True:
            print("\n" + "=" * 54)
            print("PAIRING SUCCESSFUL")
            print("=" * 54)

            print_json("Pairing Result", result)

            return result

        print("Waiting for pairing...")

        await asyncio.sleep(POLL_INTERVAL)

    raise TimeoutError(
        "Pairing was not confirmed within "
        f"{PAIRING_TIMEOUT} seconds."
    )


# ============================================================
# Main
# ============================================================

async def main():
    print("=" * 54)
    print("Codex App Server Remote Control Setup")
    print("=" * 54)

    print(f"App Server: {WS_URL}")

    async with connect(
        WS_URL,
        open_timeout=CONNECT_TIMEOUT,
        max_size=16 * 1024 * 1024,
    ) as ws:

        rpc = CodexRPC(ws)

        # 1. Initialize
        await initialize(rpc)

        # 2. Enable Remote Control
        await enable_remote_control(rpc)

        # 3. Wait for cloud connection
        await wait_for_connection(rpc)

        # 4. Generate manual pairing code
        pairing = await start_pairing(rpc)

        # 5. Confirm pairing
        await wait_for_pairing(rpc, pairing)

    print("\nSetup completed.")
    print(
        "The existing Codex App Server will continue running."
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("\nCancelled by user.")

    except Exception as exc:
        print(f"\nERROR: {exc}")
        raise SystemExit(1)
