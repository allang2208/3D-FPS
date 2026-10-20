param([string]$Label = ('svch-ballistics-' + (Get-Date -Format 'yyyyMMdd-HHmmss')))
$ErrorActionPreference = 'Stop'
$svchProject = 'D:/FPS3D/FPSGAME'
$svchLog = Join-Path $PSScriptRoot ($Label + '.log')
$svchUserDir = Join-Path $PSScriptRoot ($Label + '-user')
if (Test-Path -LiteralPath $svchLog) { throw 'Use a fresh label to preserve prior evidence.' }
$env:UE_SKIP_UBT_SDK_SETUP = '1'
$svchArguments = @(
    ('"' + $svchProject + '/FPSGAME.uproject"'),
    '/Engine/Maps/Entry?game=/Script/FPSGAME.FPSGAMEGameMode',
    '-game', '-NullRHI', '-unattended', '-nosplash', '-nosound', '-DisablePython',
    '-SkipStartupMenu', '-FixedSeed', '-UseFixedTimeStep', '-FPS=60',
    '-BallisticPresentationAudit', '-SVCHBallisticAudit',
    ('-ColdSteelProfile=SVCHBallisticAudit_' + (Get-Date -Format 'yyyyMMddHHmmss')),
    ('-UserDir="' + $svchUserDir + '/"'), ('-abslog="' + $svchLog + '"'))
$svchProcess = Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $svchArguments -WindowStyle Hidden -PassThru
Write-Output "SVCH headless diagnostic PID $($svchProcess.Id); log $svchLog"
$svchProcess.WaitForExit()
Get-Content -LiteralPath $svchLog | Select-String 'SVCH_BALLISTIC|SIGHT case='
if ($svchProcess.ExitCode -ne 0) { throw "Diagnostic exit: $($svchProcess.ExitCode)" }
if (-not (Select-String -LiteralPath $svchLog -Pattern 'SVCH_BALLISTIC_COMPLETE checks=\d+ failures=0' -Quiet)) { throw 'No successful completion record.' }
