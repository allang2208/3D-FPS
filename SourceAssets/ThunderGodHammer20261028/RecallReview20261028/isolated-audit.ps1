$ErrorActionPreference='Stop'
$taskRoot='D:\FPS3D\FPSGAME'
$taskSandbox=Join-Path $PSScriptRoot 'NativeSandbox'
New-Item -ItemType Directory -Force -Path $taskSandbox | Out-Null
Copy-Item -LiteralPath (Join-Path $taskRoot 'FPSGAME.uproject') -Destination (Join-Path $taskSandbox 'FPSGAME.uproject')
if(-not (Test-Path -LiteralPath (Join-Path $taskSandbox 'Config'))){Copy-Item -LiteralPath (Join-Path $taskRoot 'Config') -Destination (Join-Path $taskSandbox 'Config') -Recurse}
foreach($taskName in @('Content','Plugins')){
    $taskDest=Join-Path $taskSandbox $taskName
    if(-not (Test-Path -LiteralPath $taskDest)){New-Item -ItemType Junction -Path $taskDest -Target (Join-Path $taskRoot $taskName) | Out-Null}
}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'Batch occupied; isolated build was not started.'}
    & python (Join-Path $PSScriptRoot 'build_isolated.py') *> (Join-Path $PSScriptRoot 'isolated-build.log')
    if($LASTEXITCODE -ne 0){Get-Content (Join-Path $PSScriptRoot 'isolated-build.log') -Tail 12;exit $LASTEXITCODE}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $taskSandbox 'FPSGAME.uproject') -run=ThunderHammerRecallAudit ('-Out='+$PSScriptRoot+'\runtime-audit-after.json') -unattended -nop4 -nosplash -NoSound -NoLiveCoding -nullrhi -stdout -FullStdOutLogOutput ('-abslog='+$PSScriptRoot+'\isolated-engine.log') *> (Join-Path $PSScriptRoot 'isolated-console.log')
    exit $LASTEXITCODE
}finally{if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
