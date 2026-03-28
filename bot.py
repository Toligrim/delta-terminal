#!/usr/bin/env python3
import logging
import os

from deltachat_rpc_client import run_bot_cli
from deltachat_rpc_client.events import NewMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
ALLOWED_SENDER = "Anatoliy-Nosov-workmail@yandex.ru".lower()


def is_allowed_sender(event) -> bool:
    sender = (event.message_snapshot.sender.get_snapshot().address or "").strip().lower()
    return sender == ALLOWED_SENDER


def on_help(event):
    if not is_allowed_sender(event):
        return
    event.message_snapshot.chat.send_text(
        "Команды бота:\n"
        "/ping - проверка доступности\n"
        "/help - помощь"
    )


def on_ping(event):
    if not is_allowed_sender(event):
        return
    event.message_snapshot.chat.send_text("pong")


def on_text(event):
    if not is_allowed_sender(event):
        return
    text = (event.message_snapshot.text or "").strip()
    if text and not text.startswith("/"):
        event.message_snapshot.chat.send_text(f"Echo: {text}")


if __name__ == "__main__":
    if not os.getenv("DELTACHAT_EMAIL") or not os.getenv("DELTACHAT_PASSWORD"):
        raise SystemExit(
            "Set DELTACHAT_EMAIL and DELTACHAT_PASSWORD in /home/openclaw/deltachat-bot/.env"
        )

    hooks = [
        (on_help, NewMessage(command="/help")),
        (on_ping, NewMessage(command="/ping")),
        (on_text, NewMessage(is_info=False)),
    ]
    run_bot_cli(
        hooks=hooks,
        rpc_server_path="/home/openclaw/.local/bin/deltachat-rpc-server",
    )
