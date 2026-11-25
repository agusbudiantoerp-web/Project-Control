param(
    [string]$At = "20:00",
    [string]$TaskName = "AIProjectControlDailyBackup"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackupScript = Join-Path $RepoRoot "scripts\backup_workspace.py"
$PythonLauncher = (Get-Command py.exe -ErrorAction Stop).Source

try {
    $RunTime = [TimeSpan]::ParseExact($At, "hh\:mm", [Globalization.CultureInfo]::InvariantCulture)
} catch {
    throw "Waktu harus dalam format 24 jam HH:mm, contoh: 20:00"
}

$Action = New-ScheduledTaskAction -Execute $PythonLauncher -Argument "-3.11 `"$BackupScript`"" -WorkingDirectory $RepoRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.Add($RunTime))
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "Daily verified SQLite backup for the local AI Project Control workspace." -Force | Out-Null

Write-Host "Scheduled task '$TaskName' installed. Daily run time: $At"
Write-Host "Backup folder: $RepoRoot\.project_control\backups"
Write-Host "Run once now with: py -3.11 `"$BackupScript`""