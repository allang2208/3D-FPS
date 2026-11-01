$ErrorActionPreference='Stop'
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskScript=Join-Path $PSScriptRoot 'import_audio.py'
$taskEditor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
if($taskEditor.Count -gt 0){
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript $taskScript -QueueWaitSeconds 300 -RequestTimeoutSeconds 300 -MaxOutputChars 1800 -OutputFile (Join-Path $PSScriptRoot ('import-bridge-'+$taskStamp+'.json'))
    exit $LASTEXITCODE
}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while(-not $taskHeld){try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}}
    $taskEditor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    if($taskEditor.Count -gt 0){throw 'Editor started while waiting; preserve it and import through the existing bridge.'}
    while(@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool.dll'}).Count -gt 0){Start-Sleep -Seconds 5}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $taskOutput=Join-Path $PSScriptRoot ('import-'+$taskStamp+'-console.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript ('-script='+$taskScript) -unattended -nop4 -nosplash -NoSound -NoLiveCoding -nullrhi -NoShaderCompile -stdout -FullStdOutLogOutput ('-abslog='+$PSScriptRoot+'/import-'+$taskStamp+'-engine.log') *> $taskOutput
    $taskCode=$LASTEXITCODE
    Get-Content -LiteralPath $taskOutput -Tail 7
    if($taskCode -ne 0){exit $taskCode}
    if(-not (Select-String -LiteralPath $taskOutput -Pattern 'GUANLEI_AUDIO_USER_V4_SAVED' -Quiet)){throw 'This import produced no save receipt.'}
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'import_receipt.json') -Raw
}finally{
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
