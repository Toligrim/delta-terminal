# Delta Terminal Bot

Python-бот для Delta Chat, который пересылает входящие текстовые сообщения в Codex CLI и возвращает ответ обратно в чат.

## Как это работает

1. Сообщение приходит в Delta Chat.
2. `bot.py` принимает текст и вызывает `codex exec`.
3. Для следующих сообщений бот использует `codex exec resume <thread_id>`, сохраняя контекст диалога.
4. Ответ Codex отправляется обратно в тот же чат.

## Локальная схема (как сейчас настроено)

- Скрипт бота: `bot.py`
- Переменные окружения: `.env`
- Python venv: `.venv`
- Каталог аккаунтов core: `accounts/`
- Конфиг аккаунтов core: `accounts/accounts.toml`
- RPC server бинарник: `/home/openclaw/.local/bin/deltachat-rpc-server`
- systemd unit: `/home/openclaw/.config/systemd/user/deltachat-bot.service`

## Переменные окружения

Обязательные:

- `DELTACHAT_EMAIL`
- `DELTACHAT_PASSWORD`

Рекомендуемые для моста Codex:

- `DELTACHAT_ALLOWED_SENDERS` - список email через запятую. Если не задан, бот принимает сообщения от всех.
- `CODEX_BIN` - путь к бинарнику Codex (по умолчанию `codex`).
- `CODEX_WORKDIR` - рабочая директория для Codex (по умолчанию `/home/openclaw`).
- `CODEX_MODEL` - модель Codex (опционально).
- `CODEX_TIMEOUT_SEC` - timeout одного запроса к Codex в секундах (по умолчанию `600`).
- `CODEX_EXTRA_ARGS` - дополнительные аргументы для `codex exec` (опционально).
- `CODEX_THREAD_ID_FILE` - путь для файла состояния thread id (по умолчанию `/home/openclaw/deltachat-bot/.codex_thread_id`).

Пример `.env`:

```env
DELTACHAT_EMAIL=you@example.com
DELTACHAT_PASSWORD=your_password
DELTACHAT_ALLOWED_SENDERS=you@example.com
CODEX_WORKDIR=/home/openclaw
CODEX_TIMEOUT_SEC=600
```

## Команды в чате

- `/help` - список команд
- `/ping` - проверка доступности
- `/status` - показать текущий `thread_id` Codex
- `/reset` - сбросить текущую сессию Codex
- Любой другой текст - отправка в Codex

## Установка на Raspberry Pi

1. Установить Python, Delta Chat RPC server и Codex CLI.
2. Клонировать репозиторий:

```bash
git clone git@github.com:Toligrim/delta-terminal.git /home/openclaw/deltachat-bot
cd /home/openclaw/deltachat-bot
```

3. Поднять venv и установить зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install deltachat-rpc-client
```

4. Заполнить `.env`.
5. Подготовить `accounts/` и `accounts/accounts.toml`.

## Ручной запуск

```bash
cd /home/openclaw/deltachat-bot
source .venv/bin/activate
python bot.py
```

## Запуск через systemd --user

Перечитать unit:

```bash
systemctl --user daemon-reload
```

Включить автозапуск и запустить:

```bash
systemctl --user enable --now deltachat-bot.service
```

Проверка:

```bash
systemctl --user status deltachat-bot.service
journalctl --user -u deltachat-bot.service -f
```

## Безопасность

- `.env` и `accounts/` не публикуются в git.
- Файл состояния `.codex_thread_id` также исключен из репозитория.
- Для ограничения доступа указывайте `DELTACHAT_ALLOWED_SENDERS`.
