$ErrorActionPreference = 'Stop'
$studioRoot = Split-Path -Parent $PSScriptRoot
$testOutput = Join-Path $studioRoot ('output\test_tmp_' + [guid]::NewGuid().ToString('N'))
if (-not ([IO.Path]::GetFullPath($testOutput).StartsWith([IO.Path]::GetFullPath($studioRoot) + [IO.Path]::DirectorySeparatorChar))) { throw 'Test directory escaped workspace.' }
Push-Location $studioRoot
try {
    & '.\.venv\Scripts\python.exe' -X utf8 -m pytest -q "--basetemp=$testOutput" '--junitxml=docs/test-results.xml'
    exit $LASTEXITCODE
} finally { Pop-Location }
