param(
    [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$PythonExe = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
)

$ErrorActionPreference = "Stop"

Set-Location -Path $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$RunStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$RunLog = Join-Path $LogDir "scheduled_run_$RunStamp.log"

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

"Atlas scheduled run started at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $RunLog
"Project root: $ProjectRoot" | Tee-Object -FilePath $RunLog -Append
"Python: $PythonExe" | Tee-Object -FilePath $RunLog -Append

& $PythonExe "main.py" 2>&1 | Tee-Object -FilePath $RunLog -Append
$ExitCode = $LASTEXITCODE

"Atlas scheduled run finished at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') with exit code $ExitCode" |
    Tee-Object -FilePath $RunLog -Append

exit $ExitCode
