param([string]$Attempt='01')
$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    & py -3.11 -X utf8 (Join-Path $PSScriptRoot 'prepare_asset_host.py')
    if($LASTEXITCODE -ne 0){throw 'Preparing isolated asset host failed.'}
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset authoring queue timed out.'}
    $taskExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    & $taskExe (Join-Path $PSScriptRoot 'AssetHost/AssetHost.uproject') '-run=pythonscript' ("-script="+(Join-Path $PSScriptRoot 'install_assets.py')) -unattended -nosplash -NullRHI -NoSound -NoP4 -UTF8Output ("-abslog="+(Join-Path $PSScriptRoot "stage-$Attempt.log")) *> (Join-Path $PSScriptRoot "stage-console-$Attempt.log")
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;finished=(Get-Date).ToString('o');game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot "stage-receipt-$Attempt.json") -Encoding utf8
    if($taskExit -ne 0){throw "Asset authoring failed ($taskExit)."}
    Write-Output 'BEIWEI_STAGED'
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
