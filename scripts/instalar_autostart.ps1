# ============================================
# instalar_autostart.ps1 — Configura el arranque automático
# de reloj-intra al iniciar sesión en Windows.
#
# Opción 1: tarea programada (necesita permisos de administrador)
# Opción 2 (fallback): acceso directo en la carpeta "Inicio" (sin admin)
#
# Ejecutar UNA VEZ:
#   powershell -ExecutionPolicy Bypass -File scripts/instalar_autostart.ps1
# ============================================
$ErrorActionPreference = 'Continue'

$SERVER_DIR = Split-Path -Parent $PSScriptRoot
$TASK_NAME = 'RelojIntra AutoStart'

# --- Opción 1: Tarea programada al iniciar sesión (requiere admin) ---
try {
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$SERVER_DIR\scripts\start_server.ps1`""
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable
    Register-ScheduledTask -TaskName $TASK_NAME -Trigger $trigger -Action $action -Settings $settings -Description "Arranca reloj-intra (runserver 8080) al iniciar sesión" -ErrorAction Stop | Out-Null
    Write-Host "=========================================="
    Write-Host " Tarea '$TASK_NAME' registrada (método: tarea programada)."
    Write-Host "=========================================="
    exit 0
} catch {
    Write-Host " Sin permisos de administrador para tarea programada."
}

# --- Opción 2: Acceso directo en carpeta Inicio (sin admin) ---
$startup = [Environment]::GetFolderPath('Startup')
$linkPath = Join-Path $startup "Reloj-Intra.lnk"

$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($linkPath)
$lnk.TargetPath = "powershell.exe"
$lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$SERVER_DIR\scripts\start_server.ps1`""
$lnk.WorkingDirectory = $SERVER_DIR
$lnk.Save()

Write-Host "=========================================="
Write-Host " Autostart configurado (método: carpeta Inicio)."
Write-Host " Acceso directo creado en:"
Write-Host "   $linkPath"
Write-Host ""
Write-Host " Se ejecutará cada vez que inicies sesión en Windows."
Write-Host "=========================================="
