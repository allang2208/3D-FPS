$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset save queue timed out'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/AssetHost/AssetHost.uproject" -run=pythonscript "-script=$taskRoot/install_assets.py" -unattended -nop4 -nosplash -nosound -NullRHI -UTF8Output "-abslog=$taskRoot/asset-commandlet.log" *> "$taskRoot/asset-console.log"
    if($LASTEXITCODE -ne 0){throw "Asset commandlet failed: $LASTEXITCODE"}
    if(-not (Test-Path -LiteralPath "$taskRoot/asset-save.json")){throw 'Material save receipt missing'}
    Write-Output 'CHIXIAO_MATERIAL_AUTHORING_COMPLETE'
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}