param([string]$Script='read_native.py')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskPath=Join-Path $PSScriptRoot $Script
$taskTag=[IO.Path]::GetFileNameWithoutExtension($Script)
if (@(Get-Process UnrealEditor -ErrorAction SilentlyContinue).Count -gt 0) {
    & "$taskRoot/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $taskPath -RequestTimeoutSeconds 600 -OutputFile (Join-Path $PSScriptRoot ($taskTag+'-bridge-'+[guid]::NewGuid().ToString('N')+'.txt')) -MaxOutputChars 5000
    exit $LASTEXITCODE
}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    for ($taskAttempt=0; $taskAttempt -lt 20 -and -not $taskHeld; $taskAttempt++) {
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if (-not $taskHeld) {Write-Output 'Waiting for the existing asset batch lock.'}
    }
    if (-not $taskHeld) {throw 'Asset batch busy; nothing changed.'}
    if (@(Get-Process UnrealEditor -ErrorAction SilentlyContinue).Count -gt 0) {throw 'Editor opened; use its bridge.'}
    if (@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.dll')}).Count -gt 0) {throw 'Project commandlet/build active; preserve existing job.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript ("-script=$taskPath") -unattended -nop4 -nosplash -NoSound -NoLiveCoding -NullRHI -stdout -FullStdOutLogOutput ("-abslog=$PSScriptRoot/$taskTag-engine.log") *> (Join-Path $PSScriptRoot ($taskTag+'-console.log'))
    $taskExit=$LASTEXITCODE
    Write-Output "$taskTag exit=$taskExit"
    exit $taskExit
} finally {if ($taskHeld) {$taskGate.ReleaseMutex()};$taskGate.Dispose()}
