param([string]$Attempt='01')
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
& py -3.11 -X utf8 (Join-Path $taskRoot 'prepare_host.py')
if($LASTEXITCODE -ne 0){throw 'Asset host preparation failed'}
$taskExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
& $taskExe (Join-Path $taskRoot 'AssetHost/AssetHost.uproject') '-run=pythonscript' ("-script="+(Join-Path $taskRoot 'install_assets.py')) -unattended -nosplash -NullRHI -NoSound -NoP4 -UTF8Output ("-abslog="+(Join-Path $taskRoot "stage-$Attempt.log")) *> (Join-Path $taskRoot "stage-console-$Attempt.txt")
$taskExit=$LASTEXITCODE
@{exit_code=$taskExit;finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot "stage-receipt-$Attempt.json") -Encoding utf8
if($taskExit -ne 0){throw "Cyan material authoring failed ($taskExit)"}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Material publication queue timed out'}
    & py -3.11 -X utf8 (Join-Path $taskRoot 'publish.py')
    if($LASTEXITCODE -ne 0){throw 'Material/catalog publication failed'}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
& (Join-Path $taskRoot 'build.ps1') -Attempt $Attempt
