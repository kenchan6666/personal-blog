# Stop the stack started by deployment/start.ps1.
#   .\deployment\stop.ps1          stop local Mongo + Redis
#   .\deployment\stop.ps1 --prod   stop the nginx compose stack
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "start.ps1") --down @args
exit $LASTEXITCODE
