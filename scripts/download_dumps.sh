#!/usr/bin/env bash
# Скачивание дампа GeoNames cities500 в data/.
#
# В репозиторий дамп не коммитится: data/cities500.zip и data/cities500.txt
# лежат в .gitignore. После скачивания загрузите города в БД:
#   python -m scripts.load_cities --min-population 100000
#
# Запуск:
#   bash scripts/download_dumps.sh
#   bash scripts/download_dumps.sh --extract-only   # распаковать готовый zip
#   bash scripts/download_dumps.sh --force          # перекачать поверх
#
# Код возврата 0 — файлы на месте, 1 — ошибка сети/распаковки.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${ROOT}/data"
ZIP="${DATA_DIR}/cities500.zip"
TXT="${DATA_DIR}/cities500.txt"
README="${DATA_DIR}/cities500_readme.txt"
BASE_URL="https://download.geonames.org/export/dump"

EXTRACT_ONLY=0
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --extract-only) EXTRACT_ONLY=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "Неизвестный аргумент: $1" >&2; exit 1 ;;
  esac
done

mkdir -p "${DATA_DIR}"

download() {
  local url="$1" target="$2"
  if [[ -s "${target}" && "${FORCE}" -eq 0 ]]; then
    echo "Уже есть: ${target} (--force перекачает)"
    return 0
  fi
  echo "Скачиваю ${url}"
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --retry 3 --retry-delay 5 --output "${target}" "${url}"
  elif command -v wget >/dev/null 2>&1; then
    wget --tries=3 --timeout=60 --output-document="${target}" "${url}"
  else
    echo "Ошибка: нужен curl или wget" >&2
    exit 1
  fi
}

extract() {
  if [[ ! -s "${ZIP}" ]]; then
    echo "Ошибка: нет файла ${ZIP}" >&2
    exit 1
  fi
  echo "Распаковываю ${ZIP}"
  if command -v unzip >/dev/null 2>&1; then
    unzip -o "${ZIP}" -d "${DATA_DIR}"
  else
    python3 -c "import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" \
      "${ZIP}" "${DATA_DIR}"
  fi
}

if [[ "${EXTRACT_ONLY}" -eq 0 ]]; then
  download "${BASE_URL}/cities500.zip" "${ZIP}"
  download "${BASE_URL}/readme.txt" "${README}"
fi

extract

if [[ ! -s "${TXT}" ]]; then
  echo "Ошибка: после распаковки нет ${TXT}" >&2
  exit 1
fi

lines=$(wc -l < "${TXT}")
echo "Готово: ${TXT}, строк: ${lines}"
echo "Загрузка в БД: python -m scripts.load_cities --min-population 100000"
