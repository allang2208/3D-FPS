param([string[]]$Targets=@('FPSGAME','FPSGAMEEditor'),[string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
& (Join-Path $PSScriptRoot 'ClawV10/run_build.ps1') -Targets $Targets -EngineRoot $EngineRoot
exit $LASTEXITCODE
