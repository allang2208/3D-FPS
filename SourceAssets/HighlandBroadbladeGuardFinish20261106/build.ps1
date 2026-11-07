$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut="$taskRoot/Saved/HighlandBroadbladeGuardFinish20261106"
New-Item -ItemType Directory -Force -Path $taskOut | Out-Null
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch occupied; native build not started.'}
    $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME') -or
        $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')
    })
    if($taskBusy.Count){throw 'Preserving active editor/build; native build not started.'}
    $taskLog=Join-Path $taskOut ('build-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReloadFromIDE -NoLiveCoding -MaxParallelActions=4 *> $taskLog
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;log=$taskLog;gameplay_tested=$false;editor_launched=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-receipt.json') -Encoding utf8
    Get-Content -LiteralPath $taskLog -Tail 16 | Where-Object {$_ -notlike '[[]Adaptive Build[]]*'}
    if($taskExit -ne 0){throw "FPSGAMEEditor build failed ($taskExit)"}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
