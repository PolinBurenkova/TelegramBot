#!/usr/bin/env bash
# Резервная копия БД «Города+» в data/backups/.
#
# По умолчанию дамп снимается из контейнера cities_postgres через
# docker compose exec, поэтому pg_dump на хосте не нужен. Если задан
# DATABASE_URL и флаг --direct, используется локальный pg_dump.
#
# Запуск:
#   bash scripts/export_db.sh                 # дамп в data/backups/cities_bot_<ts>.sql.gz
#   bash scripts/export_db.sh --direct        # через pg_dump и DATABASE_URL
#   bash scripts/export_db.sh --out /tmp/x.sql.gz
#
# Переменные окружения (значения по умолчанию совпадают с docker-compose.yml):
#   POSTGRES_USER, POSTGRES_DB — пользователь и база внутри контейнера.
#
# Код возврата 0 — дамп создан, 1 — ошибка (нет docker/pg_dump, пустой дамп).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${ROOT}/data/backups"
POSTGRES_USER="${POSTGRES_USER:-cities}"
POSTGRES_DB="${POSTGRES_DB:-cities_bot}"
CONTAINER="${POSTGRES_CONTAINER:-cities_postgres}"

DIRECT=0
OUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --direct) DIRECT=1; shift ;;
    --out) OUT="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Неизвестный аргумент: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "${OUT}" ]]; then
  mkdir -p "${BACKUP_DIR}"
  OUT="${BACKUP_DIR}/${POSTGRES_DB}_$(date +%Y%m%d_%H%M%S).sql.gz"
fi
mkdir -p "$(dirname "${OUT}")"

echo "Дамп базы ${POSTGRES_DB} → ${OUT}"

if [[ "${DIRECT}" -eq 1 ]]; then
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "Ошибка: --direct требует DATABASE_URL" >&2
    exit 1
  fi
  command -v pg_dump >/dev/null 2>&1 || { echo "Ошибка: pg_dump не найден" >&2; exit 1; }
  pg_dump --no-owner --no-privileges "${DATABASE_URL}" | gzip -9 > "${OUT}"
else
  command -v docker >/dev/null 2>&1 || { echo "Ошибка: docker не найден" >&2; exit 1; }
  docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres \
    pg_dump --no-owner --no-privileges -U "${POSTGRES_USER}" "${POSTGRES_DB}" \
    | gzip -9 > "${OUT}"
fi

if [[ ! -s "${OUT}" ]]; then
  echo "Ошибка: дамп пустой, файл удалён" >&2
  rm -f "${OUT}"
  exit 1
fi

echo "Готово: $(du -h "${OUT}" | cut -f1)"
