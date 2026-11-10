param([string]$Version='Before')
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/SourceAssets/LeapStrike20261107/Review/$Version"
[void](New-Item -ItemType Directory -Force -Path $taskOut)
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; no review started.'}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Preserving running editor; review requires the compiled module.'}
    foreach($taskBuild in @(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})){
        try{[Diagnostics.Process]::GetProcessById($taskBuild.ProcessId).WaitForExit()}catch [ArgumentException]{}
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" '-run=LeapStrikeAudit' "-Out=$taskOut" -NullRHI -unattended -nop4 -nosound -nosplash '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$taskOut/run.log" *> "$taskOut/console.log"
    if($LASTEXITCODE -ne 0){throw "Leap review returned $LASTEXITCODE. See $taskOut/run.log"}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
