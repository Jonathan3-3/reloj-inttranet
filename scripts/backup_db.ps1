param(
    [string]$ProjectDir = (Resolve-Path "$PSScriptRoot\.."),
    [string]$BackupDir = (Join-Path $ProjectDir "backups"),
    [int]$KeepDays = 30
)

$DbFile = Join-Path $ProjectDir "db.sqlite3"

if (-not (Test-Path $DbFile)) {
    Write-Error "No se encontro db.sqlite3 en $ProjectDir"
    exit 1
}

if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

$DateStr = Get-Date -Format "yyyy-MM-dd_HHmmss"
$BackupFile = Join-Path $BackupDir "db.sqlite3.$DateStr.bak"

Copy-Item -LiteralPath $DbFile -Destination $BackupFile -Force

# Limpiar backups viejos
$Cutoff = (Get-Date).AddDays(-$KeepDays)
Get-ChildItem -Path $BackupDir -Filter "db.sqlite3.*.bak" |
    Where-Object { $_.LastWriteTime -lt $Cutoff } |
    Remove-Item -Force

Write-Output "Backup creado: $BackupFile ($((Get-Item $BackupFile).Length / 1KB) KB)"
Write-Output "Backups retenidos: $((Get-ChildItem $BackupDir -Filter 'db.sqlite3.*.bak' | Measure-Object).Count) archivos"
