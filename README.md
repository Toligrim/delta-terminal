# Delta Terminal Bot

Этот репозиторий содержит Python-бота для Delta Chat и локальную схему запуска через `systemd --user`.

## Текущая структура

- Скрипт бота: `bot.py`
- Переменные окружения: `.env`
- Виртуальное окружение Python: `.venv`
- Каталог аккаунтов DeltaChat core: `accounts/`
- Конфиг аккаунтов core: `accounts/accounts.toml`
- RPC server бинарник (symlink): `/home/openclaw/.local/bin/deltachat-rpc-server`
- `systemd` user unit: `/home/openclaw/.config/systemd/user/deltachat-bot.service`

## Требования

- Linux с `systemd --user`
- Python (рекомендуется 3.10+)
- Установленный `deltachat-rpc-server` (в текущей конфигурации через symlink в `~/.local/bin`)

## Настройка

1. Перейти в директорию проекта:

```bash
cd /home/openclaw/deltachat-bot
```

2. Подготовить виртуальное окружение (если еще не создано):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Заполнить `.env` с параметрами аккаунта (почта/пароль и другие нужные переменные бота).

4. Убедиться, что директория `accounts/` и файл `accounts/accounts.toml` существуют и содержат корректные данные.

## Ручной запуск бота

```bash
cd /home/openclaw/deltachat-bot
source .venv/bin/activate
python bot.py
```

## Запуск через systemd (user unit)

После изменения unit-файла:

```bash
systemctl --user daemon-reload
```

Запуск и включение автозапуска:

```bash
systemctl --user enable --now deltachat-bot.service
```

Проверка статуса:

```bash
systemctl --user status deltachat-bot.service
```

Логи:

```bash
journalctl --user -u deltachat-bot.service -f
```

## Безопасность

- Файл `.env` содержит секреты и не должен попадать в репозиторий.
- Каталог `accounts/` содержит локальные данные аккаунтов и также не должен публиковаться.
- В репозитории это исключено через `.gitignore`.

## GitHub

Репозиторий: `https://github.com/Toligrim/delta-terminal`
