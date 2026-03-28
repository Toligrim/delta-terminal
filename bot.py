#!/usr/bin/env python3
import json
import logging
import os
import shlex
import subprocess
import tempfile
import threading
from pathlib import Path

from deltachat_rpc_client import run_bot_cli
from deltachat_rpc_client.events import NewMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

RPC_SERVER_PATH = os.getenv("DELTACHAT_RPC_SERVER_PATH", "/home/openclaw/.local/bin/deltachat-rpc-server")
CODEX_BIN = os.getenv("CODEX_BIN", "codex")
CODEX_WORKDIR = os.getenv("CODEX_WORKDIR", "/home/openclaw")
CODEX_MODEL = os.getenv("CODEX_MODEL", "").strip()
CODEX_TIMEOUT_SEC = int(os.getenv("CODEX_TIMEOUT_SEC", "600"))
THREAD_ID_FILE = Path(os.getenv("CODEX_THREAD_ID_FILE", "/home/openclaw/deltachat-bot/.codex_thread_id"))
ALLOWED_SENDERS = {
    value.strip().lower()
    for value in os.getenv("DELTACHAT_ALLOWED_SENDERS", "").split(",")
    if value.strip()
}


def get_sender_address(event) -> str:
    return (event.message_snapshot.sender.get_snapshot().address or "").strip().lower()


def is_allowed_sender(event) -> bool:
    if not ALLOWED_SENDERS:
        return True
    return get_sender_address(event) in ALLOWED_SENDERS


def split_message(text: str, chunk_size: int = 3500) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    current = []
    current_len = 0
    for line in text.splitlines(keepends=True):
        if len(line) > chunk_size:
            if current:
                chunks.append("".join(current))
                current = []
                current_len = 0
            for i in range(0, len(line), chunk_size):
                chunks.append(line[i : i + chunk_size])
            continue
        if current_len + len(line) > chunk_size:
            chunks.append("".join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line)
    if current:
        chunks.append("".join(current))
    return chunks


class CodexBridge:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.thread_id: str | None = self._load_thread_id()
        extra_args = os.getenv("CODEX_EXTRA_ARGS", "").strip()
        self.extra_args = shlex.split(extra_args) if extra_args else []

    def _load_thread_id(self) -> str | None:
        if THREAD_ID_FILE.exists():
            thread_id = THREAD_ID_FILE.read_text(encoding="utf-8").strip()
            return thread_id or None
        return None

    def _save_thread_id(self, thread_id: str) -> None:
        THREAD_ID_FILE.write_text(thread_id + "\n", encoding="utf-8")
        self.thread_id = thread_id

    def reset_session(self) -> None:
        with self.lock:
            self.thread_id = None
            if THREAD_ID_FILE.exists():
                THREAD_ID_FILE.unlink()

    def _base_cmd(self) -> list[str]:
        cmd = [CODEX_BIN, "exec", "--skip-git-repo-check", "--json"]
        if CODEX_WORKDIR:
            cmd += ["-C", CODEX_WORKDIR]
        if CODEX_MODEL:
            cmd += ["-m", CODEX_MODEL]
        cmd += self.extra_args
        return cmd

    def _run_codex(self, cmd: list[str]) -> tuple[str, str]:
        with tempfile.NamedTemporaryFile(prefix="codex-last-", suffix=".txt", delete=False) as tmp:
            output_path = tmp.name
        full_cmd = cmd + ["-o", output_path]
        logging.info("Running Codex command: %s", " ".join(full_cmd))
        proc = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=CODEX_TIMEOUT_SEC,
            check=False,
        )
        try:
            output_text = Path(output_path).read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            output_text = ""
        finally:
            Path(output_path).unlink(missing_ok=True)
        if proc.returncode != 0:
            raise RuntimeError(
                f"Codex exited with code {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )
        return proc.stdout, output_text

    @staticmethod
    def _extract_thread_id(jsonl_text: str) -> str | None:
        for raw in jsonl_text.splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "thread.started":
                return event.get("thread_id")
        return None

    def ask(self, prompt: str) -> str:
        with self.lock:
            if self.thread_id:
                try:
                    stdout, answer = self._run_codex(
                        self._base_cmd() + ["resume", self.thread_id, prompt]
                    )
                except Exception as exc:
                    logging.warning("Resume failed, starting new session: %s", exc)
                    stdout, answer = self._run_codex(self._base_cmd() + [prompt])
            else:
                stdout, answer = self._run_codex(self._base_cmd() + [prompt])

            thread_id = self._extract_thread_id(stdout)
            if thread_id:
                self._save_thread_id(thread_id)
            if not answer:
                return "Codex не вернул текстовый ответ."
            return answer


BRIDGE = CodexBridge()


def send_reply(chat, text: str) -> None:
    for chunk in split_message(text):
        chat.send_text(chunk)


def get_chat_encryption_info(event) -> str:
    try:
        info = event.message_snapshot.chat.get_encryption_info()
    except Exception as exc:
        return f"Не удалось получить encryption info: {exc}"
    return (info or "").strip() or "Encryption info недоступен."


def on_help(event):
    if not is_allowed_sender(event):
        return
    event.message_snapshot.chat.send_text(
        "Команды:\n"
        "/help - помощь\n"
        "/ping - проверка доступности\n"
        "/status - текущий thread id Codex\n"
        "/encryption - статус шифрования текущего чата\n"
        "/reset - сбросить сессию Codex\n"
        "Любой другой текст отправляется в Codex."
    )


def on_ping(event):
    if not is_allowed_sender(event):
        return
    event.message_snapshot.chat.send_text("pong")


def on_status(event):
    if not is_allowed_sender(event):
        return
    if BRIDGE.thread_id:
        event.message_snapshot.chat.send_text(f"Codex thread: {BRIDGE.thread_id}")
    else:
        event.message_snapshot.chat.send_text("Codex thread еще не создан.")


def on_reset(event):
    if not is_allowed_sender(event):
        return
    BRIDGE.reset_session()
    event.message_snapshot.chat.send_text("Сессия Codex сброшена.")


def on_encryption(event):
    if not is_allowed_sender(event):
        return
    send_reply(event.message_snapshot.chat, get_chat_encryption_info(event))


def on_text(event):
    if not is_allowed_sender(event):
        return
    text = (event.message_snapshot.text or "").strip()
    if not text or text.startswith("/"):
        return

    sender = get_sender_address(event)
    encryption_info = get_chat_encryption_info(event).replace("\n", " | ")
    logging.info("Incoming message from %s", sender)
    logging.info("Chat encryption info: %s", encryption_info)
    chat = event.message_snapshot.chat
    chat.send_text("Принято. Отправляю запрос в Codex...")
    try:
        answer = BRIDGE.ask(text)
    except subprocess.TimeoutExpired:
        send_reply(chat, "Ошибка: Codex не ответил вовремя (timeout).")
        return
    except Exception as exc:
        logging.exception("Codex request failed")
        send_reply(chat, f"Ошибка при запросе к Codex:\n{exc}")
        return

    send_reply(chat, answer)


if __name__ == "__main__":
    if not os.getenv("DELTACHAT_EMAIL") or not os.getenv("DELTACHAT_PASSWORD"):
        raise SystemExit(
            "Set DELTACHAT_EMAIL and DELTACHAT_PASSWORD in /home/openclaw/deltachat-bot/.env"
        )

    hooks = [
        (on_help, NewMessage(command="/help")),
        (on_ping, NewMessage(command="/ping")),
        (on_status, NewMessage(command="/status")),
        (on_encryption, NewMessage(command="/encryption")),
        (on_reset, NewMessage(command="/reset")),
        (on_text, NewMessage(is_info=False)),
    ]
    run_bot_cli(
        hooks=hooks,
        rpc_server_path=RPC_SERVER_PATH,
    )
