param([string]$ScriptName='import_assets.py')
$ErrorActionPreference='Stop'
$taskScript=Join-Path $PSScriptRoot $ScriptName
$taskEditor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
if($taskEditor.Count -gt 0){
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript $taskScript -QueueWaitSeconds 60 -RequestTimeoutSeconds 300 -MaxOutputChars 2500 -OutputFile (Join-Path $PSScriptRoot ('import-bridge-'+[guid]::NewGuid().ToString('N')+'.json'))
    exit $LASTEXITCODE
}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    for($taskAttempt=0;$taskAttempt -lt 20 -and -not $taskHeld;$taskAttempt++){
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    }
    if(-not $taskHeld){throw 'Asset batch remains busy; no import started.'}
    $taskEditor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {(-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    if($taskEditor.Count -gt 0){throw 'Editor started while waiting. Keep assets untouched and use the existing bridge.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript ('-script='+$taskScript) -unattended -nop4 -nosplash -NoSound -NoLiveCoding -nullrhi -NoShaderCompile -stdout -FullStdOutLogOutput ('-abslog='+$PSScriptRoot+'\import-engine.log') *> (Join-Path $PSScriptRoot 'import-console.log')
    exit $LASTEXITCODE
}finally{
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
