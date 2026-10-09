$ErrorActionPreference = 'Stop'
$studioRoot = Split-Path -Parent $PSScriptRoot
$studioPython = Join-Path $studioRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $studioPython)) { throw 'Run scripts\install.ps1 first.' }
$previousPythonPath = $env:PYTHONPATH
try {
    $env:PYTHONPATH = Join-Path $studioRoot 'src'
    & $studioPython -X utf8 -m ai_drama @args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { $env:PYTHONPATH = $previousPythonPath }
