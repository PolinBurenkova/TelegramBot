#!/usr/bin/env bash
# Восстановление БД «Города+» из дампа, созданного scripts/export_db.sh.
#
# Внимание: восстанавливает данные поверх текущей схемы — существующие
# строки не удаляются автоматически, поэтому импорт в непустую базу может
# упасть на конфликте уникальных ключей. Для чистого восстановления сначала
# выполните `python -m scripts.reset_db --yes`.
#
# Запуск:
#   bash scripts/import_db.sh data/backups/cities_bot_20240101_120000.sql.gz
#   bash scripts/import_db.sh dump.sql.gz --direct
#
# Код возврата 0 — импорт завершён, 1 — ошибка (нет файла/docker/psql).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POSTGRES_USER="${POSTGRES_USER:-cities}"
POSTGRES_DB="${POSTGRES_DB:-cities_bot}"

FILE="${1:-}"
DIRECT=0

if [[ -z "${FILE}" || "${FILE}" == "-h" || "${FILE}" == "--help" ]]; then
  sed -n '2,18p' "$0"
  [[ -z "${FILE}" ]] && exit 1
  exit 0
fi
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --direct) DIRECT=1; shift ;;
    *) echo "Неизвестный аргумент: $1" >&2; exit 1 ;;
  esac
done

if [[ ! -f "${FILE}" ]]; then
  echo "Ошибка: файл не найден — ${FILE}" >&2
  exit 1
fi

case "${FILE}" in
  *.gz) READ=(gzip -dc "${FILE}") ;;
  *)    READ=(cat "${FILE}") ;;
esac

echo "Импорт ${FILE} в базу ${POSTGRES_DB}"

if [[ "${DIRECT}" -eq 1 ]]; then
  if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "Ошибка: --direct требует DATABASE_URL" >&2
    exit 1
  fi
  command -v psql >/dev/null 2>&1 || { echo "Ошибка: psql не найден" >&2; exit 1; }
  "${READ[@]}" | psql --set ON_ERROR_STOP=1 "${DATABASE_URL}"
else
  command -v docker >/dev/null 2>&1 || { echo "Ошибка: docker не найден" >&2; exit 1; }
  "${READ[@]}" | docker compose -f "${ROOT}/docker-compose.yml" exec -T postgres \
    psql --set ON_ERROR_STOP=1 -U "${POSTGRES_USER}" "${POSTGRES_DB}"
fi

echo "Готово"
