$process = Start-Process -WindowStyle Hidden -FilePath "python" -ArgumentList "manage.py runserver 0.0.0.0:8080" -PassThru
$process.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal
Write-Host "Servidor corriendo en http://10.10.0.198:8080/ (PID: $($process.Id))"
Write-Host "Para detenerlo: Task Manager -> matar python.exe o usar: Stop-Process -Id $($process.Id)"
