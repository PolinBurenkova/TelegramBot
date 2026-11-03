#!/usr/bin/env bash
# Развёртывание «Города+» на Debian 13 (trixie) нативно, без Docker:
#   Python 3.13/3.12 + PostgreSQL (solar/solarnotfound, БД cities_bot) + Redis + systemd.
#
# Запуск (от root):
#   bash deploy_debian13.sh
#
# Переопределяется переменными окружения:
#   REPO_URL, BRANCH, APP_DIR, APP_USER,
#   DB_NAME=cities_bot, DB_USER=solar, DB_PASSWORD=solarnotfound,
#   ENV_FILE_SRC=/root/cities_bot.env   (готовый .env с вашей машины)
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/PolinBurenkova/TelegramBot.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-/opt/cities-plus-bot}"
APP_USER="${APP_USER:-citiesbot}"
DB_NAME="${DB_NAME:-cities_bot}"
DB_USER="${DB_USER:-solar}"
DB_PASSWORD="${DB_PASSWORD:-solarnotfound}"
ENV_FILE_SRC="${ENV_FILE_SRC:-/root/cities_bot.env}"
SERVICE_NAME="${SERVICE_NAME:-cities-bot}"

log() { printf '\n=== %s ===\n' "$*"; }
die() { printf '\nОШИБКА: %s\n' "$*" >&2; exit 1; }

# set_env KEY VALUE FILE — заменить строку KEY=... или добавить её.
set_env() {
    local key="$1" value="$2" file="$3"
    if grep -qE "^${key}=" "$file"; then
        sed -i -E "s|^${key}=.*|${key}=${value}|" "$file"
    else
        printf '%s=%s\n' "$key" "$value" >> "$file"
    fi
}

log "1/9 Проверка системы"
[[ $EUID -eq 0 ]] || die "запустите скрипт от root: sudo -i && bash deploy_debian13.sh"
# shellcheck disable=SC1091
. /etc/os-release
printf 'ОС: %s\n' "${PRETTY_NAME:-неизвестно}"
printf 'Ядро: %s\n' "$(uname -r)"

log "2/9 Установка пакетов (python3, venv, pip, git, postgresql, redis, build tools)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    python3 python3-venv python3-dev python3-pip \
    git curl ca-certificates \
    postgresql postgresql-contrib libpq-dev \
    redis-server build-essential

log "3/9 Проверка версии Python"
PY_VERSION="$(python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
PY_MAJOR_MINOR="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
printf 'Найден Python %s\n' "$PY_VERSION"
case "$PY_MAJOR_MINOR" in
    3.12|3.13) : ;;
    *) die "нужен Python 3.12 или 3.13, найден $PY_VERSION. На Debian 13 python3 — это 3.13; проверьте, что не установлен старый python3 из backports." ;;
esac

log "4/9 PostgreSQL: роль ${DB_USER} и база ${DB_NAME}"
systemctl enable --now postgresql
# Роль создаётся один раз; пароль выставляется всегда, чтобы совпадал с .env.
sudo -u postgres psql -v ON_ERROR_STOP=1 -q <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}') THEN
        CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
    END IF;
END
\$\$;
ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';
SQL

if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1; then
    printf 'База %s уже существует\n' "$DB_NAME"
else
    sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"
    printf 'База %s создана\n' "$DB_NAME"
fi
# Схема public должна принадлежать пользователю, иначе миграции не создадут таблицы.
sudo -u postgres psql -v ON_ERROR_STOP=1 -q -d "$DB_NAME" \
    -c "ALTER SCHEMA public OWNER TO ${DB_USER};" \
    -c "GRANT ALL ON SCHEMA public TO ${DB_USER};"

log "5/9 Redis (кеш и FSM)"
systemctl enable --now redis-server
redis-cli ping >/dev/null 2>&1 && printf 'Redis отвечает PONG\n' || printf 'ПРЕДУПРЕЖДЕНИЕ: redis-cli не ответил\n'

log "6/9 Пользователь ${APP_USER} и код из ${REPO_URL}"
if ! id -u "$APP_USER" >/dev/null 2>&1; then
    useradd --system --create-home --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi
mkdir -p "$APP_DIR"

if [[ -d "$APP_DIR/.git" ]]; then
    git -C "$APP_DIR" fetch --prune origin
    git -C "$APP_DIR" checkout "$BRANCH"
    git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
else
    # GIT_TERMINAL_PROMPT=0: не зависать на запросе пароля, если репозиторий приватный.
    if ! GIT_TERMINAL_PROMPT=0 git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"; then
        die "не удалось склонировать $REPO_URL. Если репозиторий приватный — используйте токен:
    REPO_URL=https://<ЛОГИН>:<PERSONAL_ACCESS_TOKEN>@github.com/PolinBurenkova/TelegramBot.git bash deploy_debian13.sh
  или загрузите архив репозитория в $APP_DIR и распакуйте его."
    fi
fi
chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

log "7/9 Виртуальное окружение и зависимости"
# Страховка: в ранних коммитах requirements.txt лежал в UTF-16 с BOM, из-за чего
# pip на Linux спотыкается. Приводим файл к UTF-8, если заметили BOM.
sudo -u "$APP_USER" python3 - "$APP_DIR/requirements.txt" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
raw = path.read_bytes()
if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
    path.write_text(raw.decode("utf-16"), encoding="utf-8")
    print("requirements.txt: UTF-16 -> UTF-8")
elif raw[:3] == b"\xef\xbb\xbf":
    path.write_text(raw.decode("utf-8-sig"), encoding="utf-8")
    print("requirements.txt: BOM удалён")
else:
    print("requirements.txt: кодировка в порядке")
PY

sudo -u "$APP_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" -m pip install --upgrade pip wheel
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"

log "8/9 Конфигурация .env"
ENV_FILE="$APP_DIR/.env"
if [[ -f "$ENV_FILE_SRC" ]]; then
    install -o "$APP_USER" -g "$APP_USER" -m 600 "$ENV_FILE_SRC" "$ENV_FILE"
    printf 'Скопирован %s -> %s\n' "$ENV_FILE_SRC" "$ENV_FILE"
elif [[ -f "$ENV_FILE" ]]; then
    printf 'Использую существующий %s\n' "$ENV_FILE"
else
    install -o "$APP_USER" -g "$APP_USER" -m 600 "$APP_DIR/.env.example" "$ENV_FILE"
    printf 'Создан %s из .env.example — впишите BOT_TOKEN!\n' "$ENV_FILE"
fi

# Серверные значения: локальный Postgres/Redis, production, без прокси.
set_env DATABASE_URL "postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}" "$ENV_FILE"
set_env DB_HOST "localhost" "$ENV_FILE"
set_env DB_PORT "5432" "$ENV_FILE"
set_env DB_NAME "$DB_NAME" "$ENV_FILE"
set_env DB_USER "$DB_USER" "$ENV_FILE"
set_env DB_PASSWORD "$DB_PASSWORD" "$ENV_FILE"
set_env ENVIRONMENT "production" "$ENV_FILE"
set_env LOG_LEVEL "INFO" "$ENV_FILE"
set_env REDIS_URL "redis://127.0.0.1:6379/0" "$ENV_FILE"
set_env FSM_REDIS_URL "redis://127.0.0.1:6379/1" "$ENV_FILE"
set_env BOT_PROXY "" "$ENV_FILE"
set_env BOT_TRANSPORT "auto" "$ENV_FILE"
set_env BOT_PROXY_FALLBACK_DIRECT "true" "$ENV_FILE"
chown "$APP_USER":"$APP_USER" "$ENV_FILE"
chmod 600 "$ENV_FILE"

if ! grep -qE '^BOT_TOKEN=.+' "$ENV_FILE"; then
    die "в $ENV_FILE не заполнен BOT_TOKEN. Впишите токен от @BotFather и запустите скрипт снова."
fi
printf 'BOT_TOKEN заполнен, DATABASE_URL -> localhost/%s\n' "$DB_NAME"

log "9/9 Миграции, сиды, systemd"
# Миграции читают DATABASE_URL из app.config (см. migrations/env.py).
sudo -u "$APP_USER" bash -c "cd '$APP_DIR' && '$APP_DIR/.venv/bin/alembic' upgrade head"

# Сид городов идемпотентен: существующие записи пропускаются.
sudo -u "$APP_USER" bash -c "cd '$APP_DIR' && mkdir -p data && '$APP_DIR/.venv/bin/python' -m scripts.seed_cities_seed" || \
    printf 'ПРЕДУПРЕЖДЕНИЕ: сид городов не загрузился (не критично, повторите вручную)\n'

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<UNIT
[Unit]
Description=Cities Plus Telegram bot (@CitiesPlusBot)
After=network-online.target postgresql.service redis-server.service
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${APP_DIR}/.venv/bin/python run.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
sleep 5

printf '\n=== Итог ===\n'
systemctl --no-pager --full status "$SERVICE_NAME" | head -n 12 || true
printf '\nПоследние строки лога:\n'
journalctl -u "$SERVICE_NAME" -n 15 --no-pager || true

cat <<'DONE'

Готово. Полезные команды:
  systemctl restart cities-bot      # перезапустить
  systemctl stop cities-bot         # остановить
  journalctl -u cities-bot -f       # смотреть лог в реальном времени
  journalctl -u cities-bot -n 100   # последние 100 строк
  sudo -u postgres psql cities_bot  # зайти в базу
DONE
