#!/usr/bin/env python3
import os
import sys

from deltachat_rpc_client import DeltaChat, Rpc

ACCOUNTS_DIR = "/home/openclaw/deltachat-bot/accounts"
RPC_SERVER_PATH = os.getenv("DELTACHAT_RPC_SERVER_PATH", "/home/openclaw/.local/bin/deltachat-rpc-server")


def read_qrdata() -> str:
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip()
    env_val = os.getenv("SECUREJOIN_QRDATA", "").strip()
    if env_val:
        return env_val
    print("Paste invite link (https://i.delta.chat/...) and press Enter:")
    return input().strip()


def main() -> int:
    qrdata = read_qrdata()
    if not qrdata:
        print("Error: invite link is empty", file=sys.stderr)
        return 2

    if "i.delta.chat" not in qrdata and "OPENPGP4FPR" not in qrdata:
        print("Warning: value does not look like a Delta Chat securejoin link.", file=sys.stderr)

    with Rpc(accounts_dir=ACCOUNTS_DIR, rpc_server_path=RPC_SERVER_PATH) as rpc:
        dc = DeltaChat(rpc)
        accounts = dc.get_all_accounts()
        if not accounts:
            print("Error: no Delta Chat accounts found", file=sys.stderr)
            return 3

        account = accounts[0]
        rpc.start_io_for_all_accounts()

        print("Starting secure-join handshake...")
        chat = account.secure_join(qrdata)
        account.wait_for_securejoin_joiner_success()

        print("SecureJoin OK")
        try:
            info = chat.get_encryption_info() or ""
            print("\nEncryption info:\n")
            print(info.strip())
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
