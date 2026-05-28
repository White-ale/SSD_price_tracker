$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonPath = Join-Path $ProjectRoot "venv\Scripts\python.exe"

Set-Location $ProjectRoot
& $PythonPath "main.py" "--api"
