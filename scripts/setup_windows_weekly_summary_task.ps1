param(
    [string]$TaskName = "Atlas Lite Weekly Summary",
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$RunDay = "Sunday",
    [string]$RunTime = "08:00"
)

$ErrorActionPreference = "Stop"

$RunnerPath = Join-Path $ProjectRoot "scripts\run_atlas_weekly.ps1"
if (-not (Test-Path $RunnerPath)) {
    throw "Runner script not found: $RunnerPath"
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RunnerPath`" -ProjectRoot `"$ProjectRoot`"" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $RunDay -At $RunTime
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Runs Atlas Lite and generates the Weekly Research Summary." `
    -Force | Out-Null

Write-Host "Scheduled task '$TaskName' created or updated."
Write-Host "Schedule: weekly on $RunDay at $RunTime"
Write-Host "Project: $ProjectRoot"
Write-Host "Runner: $RunnerPath"
