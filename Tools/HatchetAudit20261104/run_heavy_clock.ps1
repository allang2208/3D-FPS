$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$oldSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$held=$true;throw 'Previous UE batch interrupted; preserved.'}
    if(-not $held){throw 'UE batch occupied; nothing started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'}){throw 'Existing build preserved.'}
    $run=Join-Path $PSScriptRoot ('HeavyClock-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Force -Path $run | Out-Null
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=KukriNetworkAudit -HeavyOnly -unattended -nop4 -nosplash -nullrhi -nosound '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-UserDir=$run/User/" "-Output=$run/result.json" "-abslog=$run/commandlet.log" *> "$run/console.log"
    if($LASTEXITCODE -ne 0){throw "Heavy clock checks failed: $LASTEXITCODE; $run"}
    Write-Output "HEAVY_CLOCK_PASS $run"
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$oldSdk
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
