param([ValidateSet('audit_assets.py','fix_carrier.py')][string]$Script='audit_assets.py')
$ErrorActionPreference='Stop'
$hatchetGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$hatchetHeld=$false
$hatchetOldSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try{$hatchetHeld=$hatchetGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$hatchetHeld=$true;throw 'Previous UE batch interrupted; preserved.'}
    if(-not $hatchetHeld){throw 'UE batch busy; nothing started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -match 'UnrealBuildTool' -and $_.Name -in @('dotnet.exe','UnrealBuildTool.exe')}){throw 'Existing build preserved.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended -nop4 -nosplash -nullrhi -nosound '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$PSScriptRoot/$Script.log" *> "$PSScriptRoot/$Script-console.log"
    if($LASTEXITCODE -ne 0){throw "Asset commandlet failed: $LASTEXITCODE"}
    Write-Output 'HATCHET_SAVED_ASSETS_DONE'
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$hatchetOldSdk
    if($hatchetHeld){$hatchetGate.ReleaseMutex()};$hatchetGate.Dispose()
}
