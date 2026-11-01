$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
Write-Output 'Waiting for UE build/editor access; no editor will be opened.'
while($true){
    $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.dll') -or
        ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME')
    })
    if($taskBusy.Count -eq 0){break}
    Start-Sleep -Seconds 5
}
$taskLog=Join-Path $PSScriptRoot ('build-'+$taskStamp+'.log')
$taskOutput=Join-Path $PSScriptRoot ('build-'+$taskStamp+'-console.log')
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 -ForceHeaderGeneration -NoUBTMakefiles "-Log=$taskLog" *> $taskOutput
$taskCode=$LASTEXITCODE
[ordered]@{target='FPSGAMEEditor';exit_code=$taskCode;log=$taskLog;finished=(Get-Date).ToString('o');gameplay_tested=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot ('build-'+$taskStamp+'-receipt.json')) -Encoding utf8
Get-Content -LiteralPath $taskOutput -Tail 9
if($taskCode -ne 0){exit $taskCode}
$taskScript=Join-Path $PSScriptRoot 'import_audio.py'
$taskEditor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
if($taskEditor.Count -gt 0){
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript $taskScript -QueueWaitSeconds 60 -RequestTimeoutSeconds 300 -MaxOutputChars 1800 -OutputFile (Join-Path $PSScriptRoot ('import-bridge-'+$taskStamp+'.json'))
    exit $LASTEXITCODE
}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    while(-not $taskHeld){try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}}
    $taskEditor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    if($taskEditor.Count -gt 0){throw 'Editor started while waiting; use the existing bridge for the saved import script.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript ('-script='+$taskScript) -unattended -nop4 -nosplash -NoSound -NoLiveCoding -nullrhi -NoShaderCompile -stdout -FullStdOutLogOutput ('-abslog='+$PSScriptRoot+'/import-'+$taskStamp+'-engine.log') *> (Join-Path $PSScriptRoot ('import-'+$taskStamp+'-console.log'))
    $taskCode=$LASTEXITCODE
    if($taskCode -eq 0 -and -not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'import_receipt.json'))){throw 'Commandlet exited without an audio save receipt.'}
    if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'import_receipt.json')){Get-Content -LiteralPath (Join-Path $PSScriptRoot 'import_receipt.json') -Raw}
    exit $taskCode
}finally{
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
