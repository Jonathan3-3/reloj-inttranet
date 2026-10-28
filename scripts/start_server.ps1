# ============================================
# start_server.ps1 — Arranca reloj-intra en 2do plano
# Uso: powershell -ExecutionPolicy Bypass -File scripts/start_server.ps1
# ============================================
$ErrorActionPreference = 'Stop'

$SERVER_DIR = Split-Path -Parent $PSScriptRoot
Set-Location $SERVER_DIR

# Usar python del venv si existe, si no el del sistema
if (Test-Path "$SERVER_DIR\.venv\Scripts\python.exe") {
    $PYTHON = "$SERVER_DIR\.venv\Scripts\python.exe"
} else {
    $PYTHON = "python"
}

# Cargar variables del .env (por si manage.py no tiene python-dotenv)
$envFile = Join-Path $SERVER_DIR ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $k, $v = $line -split '=', 2
            $v = $v.Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($k.Trim(), $v, 'Process')
        }
    }
}

# Verificar si ya hay un proceso corriendo (evita duplicados)
$yaCorre = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'manage.py runserver 0.0.0.0:8080' }
if ($yaCorre) {
    Write-Host "Ya hay un servidor corriendo (PID: $($yaCorre.ProcessId -join ',')). No se hace nada."
    exit 0
}

# Crear carpeta de logs
New-Item -ItemType Directory -Path "$SERVER_DIR\logs" -Force | Out-Null
$logFile = Join-Path $SERVER_DIR "logs\server.log"

# Lanzar en 2do plano via cmd con `start /b` (oculto, redirige salida a log).
# cmd regresa al instante y el server queda corriendo desapegado.
$quotedPython = "`"$PYTHON`""
$cmdLine = "/c start `"`" /b $quotedPython manage.py runserver 0.0.0.0:8080 --noreload > `"$logFile`" 2>&1"
Start-Process -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList $cmdLine -WorkingDirectory $SERVER_DIR | Out-Null

# Esperar y capturar el PID real del proceso python
$serverPid = -1
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Milliseconds 500
    $proc = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'manage.py runserver 0.0.0.0:8080' } |
        Select-Object -First 1
    if ($proc) {
        $serverPid = [int]$proc.ProcessId
        break
    }
}

# Guardar PID y bajar prioridad
if ($serverPid -gt 0) {
    $serverPid | Out-File -FilePath "$SERVER_DIR\logs\server.pid" -Encoding ascii
    try {
        $p = Get-Process -Id $serverPid -ErrorAction Stop
        $p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal
    } catch {}
}

$ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notmatch '^127\.' -and $_.IPAddress -notmatch '^169\.' } |
    Select-Object -First 1).IPAddress

Write-Host "=========================================="
Write-Host " Reloj-Intra arrancando..."
if ($ip) { Write-Host " URL: http://$ip`:8080/" }
Write-Host (" PID: " + $(if ($serverPid -gt 0) { $serverPid } else { 'pendiente (revisa logs\server.log)' }))
Write-Host " Log: $logFile"
Write-Host " Para detener: Stop-Process -Id $serverPid"
Write-Host "=========================================="
