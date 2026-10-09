param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$studioRoot = Split-Path -Parent $PSScriptRoot
& $Python -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'"
if ($LASTEXITCODE -ne 0) { throw 'Please specify a Python 3.11+ executable with -Python.' }
$studioPython = Join-Path $studioRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $studioPython)) {
    & $Python -m venv (Join-Path $studioRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'venv creation failed. No ComfyUI environment was changed.' }
}
& $studioPython -m pip install --index-url https://pypi.org/simple -e "$studioRoot[test]"
if ($LASTEXITCODE -ne 0) { throw 'Project dependency installation failed.' }
Write-Output 'Installed only project dependencies; ComfyUI/model environment was not changed.'
