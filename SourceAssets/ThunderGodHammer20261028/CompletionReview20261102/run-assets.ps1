param([string]$Script='audit_assets.py')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    for($attempt=0;$attempt -lt 20 -and -not $taskHeld;$attempt++) {
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    }
    if(-not $taskHeld){throw 'UE batch occupied; no audit started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE processes preserved.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'}){throw 'Existing build preserved.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended -nop4 -nosplash -NoSound -NoLiveCoding -NullRHI "-abslog=$PSScriptRoot/$Script.log" *> (Join-Path $PSScriptRoot ($Script+'-console.log'))
    if($LASTEXITCODE -ne 0){throw 'Saved asset readback failed; see asset-load.log.'}
    Write-Output 'SAVED_ASSET_READBACK_COMPLETE'
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
