# =============================================================================
# schedule_windows.ps1 — Register ETL pipeline with Windows Task Scheduler
# =============================================================================
# Usage (run as Administrator in PowerShell):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\scripts\schedule_windows.ps1
#
# Schedules the pipeline to run daily at 06:00 AM.
# =============================================================================

param(
    [string]$TaskName   = "ETL_Sales_Pipeline",
    [string]$RunTime    = "06:00",
    [string]$PythonExe  = "python"      # Change to full path if needed
)

$ProjectDir  = (Resolve-Path "$PSScriptRoot\..").Path
$PipelinePy  = Join-Path $ProjectDir "pipeline.py"
$LogFile     = Join-Path $ProjectDir "logs\task_scheduler.log"

Write-Host "──────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host "  ETL Pipeline — Windows Task Scheduler Setup" -ForegroundColor Cyan
Write-Host "──────────────────────────────────────────────" -ForegroundColor Cyan
Write-Host "  Task name  : $TaskName"
Write-Host "  Project    : $ProjectDir"
Write-Host "  Schedule   : Daily at $RunTime"
Write-Host "──────────────────────────────────────────────" -ForegroundColor Cyan

# Ensure logs directory exists
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectDir "logs") | Out-Null

# Build the action: python pipeline.py >> logs\task_scheduler.log 2>&1
$Action  = New-ScheduledTaskAction `
    -Execute    "cmd.exe" `
    -Argument   "/c `"cd /d `"$ProjectDir`" && $PythonExe `"$PipelinePy`" >> `"$LogFile`" 2>&1`"" `
    -WorkingDirectory $ProjectDir

$Trigger = New-ScheduledTaskTrigger -Daily -At $RunTime

$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 5)

# Register (or update) the task
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "  ♻️  Existing task removed — re-registering …"
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action   $Action   `
    -Trigger  $Trigger  `
    -Settings $Settings `
    -RunLevel Highest   | Out-Null

Write-Host ""
Write-Host "  ✅  Task '$TaskName' registered successfully!" -ForegroundColor Green
Write-Host "  View in Task Scheduler → Task Scheduler Library"
Write-Host "  Run now: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Remove : Unregister-ScheduledTask -TaskName '$TaskName'"
