$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PythonPath = Join-Path $ProjectRoot "venv\Scripts\python.exe"

$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument "main.py --api" `
    -WorkingDirectory $ProjectRoot

$Trigger = New-ScheduledTaskTrigger -AtLogOn
$UserId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Principal = New-ScheduledTaskPrincipal `
    -UserId $UserId `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName "SSD Price Tracker API" `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Description "Start SSD Price Tracker API at user logon" `
    -Force
