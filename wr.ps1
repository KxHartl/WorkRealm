# WorkRealm launcher for PowerShell:  .\wr.ps1 new MyTask [-- flags]
# Put the WorkRealm folder on PATH to call it as `wr` from anywhere.
python "$PSScriptRoot\wr.py" @args
exit $LASTEXITCODE
