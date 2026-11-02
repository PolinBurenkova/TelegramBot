<#
.SYNOPSIS
    Скачивание дампа GeoNames cities500 в data/ (Windows).

.DESCRIPTION
    Дамп в репозиторий не коммитится (data/cities500.zip, data/cities500.txt
    в .gitignore). После скачивания загрузите города в БД:

        python -m scripts.load_cities --min-population 100000

.PARAMETER ExtractOnly
    Не скачивать, только распаковать уже лежащий data/cities500.zip.

.PARAMETER Force
    Перекачать файлы поверх существующих.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\download_dumps.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\download_dumps.ps1 -ExtractOnly
#>
[CmdletBinding()]
param(
    [switch]$ExtractOnly,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$dataDir = Join-Path $root 'data'
$zipPath = Join-Path $dataDir 'cities500.zip'
$txtPath = Join-Path $dataDir 'cities500.txt'
$readmePath = Join-Path $dataDir 'cities500_readme.txt'
$baseUrl = 'https://download.geonames.org/export/dump'

if (-not (Test-Path -LiteralPath $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

function Save-Dump {
    param([string]$Url, [string]$Target)

    $existing = Get-Item -LiteralPath $Target -ErrorAction SilentlyContinue
    if ($null -ne $existing -and $existing.Length -gt 0 -and -not $Force) {
        Write-Host ("[skip] уже есть: {0}" -f $Target)
        return
    }

    Write-Host ("[get ] {0}" -f $Url)
    $progress = $ProgressPreference
    $ProgressPreference = 'SilentlyContinue'
    try {
        Invoke-WebRequest -Uri $Url -OutFile $Target -UseBasicParsing -MaximumRedirection 5
    }
    finally {
        $ProgressPreference = $progress
    }

    $result = Get-Item -LiteralPath $Target
    if ($result.Length -eq 0) {
        throw ("файл пустой: {0}" -f $Target)
    }
    Write-Host ("[ok  ] {0} ({1:N0} байт)" -f $Target, $result.Length)
}

if (-not $ExtractOnly) {
    Save-Dump -Url "$baseUrl/cities500.zip" -Target $zipPath
    Save-Dump -Url "$baseUrl/readme.txt" -Target $readmePath
}

if (-not (Test-Path -LiteralPath $zipPath)) {
    throw ("нет файла {0}" -f $zipPath)
}

Write-Host ("[unzip] {0}" -f $zipPath)
Expand-Archive -LiteralPath $zipPath -DestinationPath $dataDir -Force

$txt = Get-Item -LiteralPath $txtPath -ErrorAction SilentlyContinue
if ($null -eq $txt -or $txt.Length -eq 0) {
    throw ("после распаковки нет {0}" -f $txtPath)
}

$lines = (Get-Content -LiteralPath $txtPath -ReadCount 0).Count
Write-Host ("[ok  ] {0}: строк {1:N0}" -f $txtPath, $lines)
Write-Host 'Дальше: python -m scripts.load_cities --min-population 100000'
