$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while (-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(10000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if(-not $taskHeld){continue}
        $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*') -or
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -like '*FPSGAME.uproject*')
        })
        if($taskBusy.Count -gt 0){$taskGate.ReleaseMutex();$taskHeld=$false;Start-Sleep -Seconds 10}
    }
    $taskEditor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -like '*FPSGAME.uproject*'})
    if($taskEditor.Count -gt 0){throw 'FPSGAME editor is open; preserve it. Full Editor build needs the existing editor to close.'}
    $taskLog=Join-Path $PSScriptRoot ('build-editor-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    Write-Output "BLADE_MATERIAL_STATS_BUILD_STARTED $taskLog"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$taskRoot/FPSGAME.uproject" -NoHotReloadFromIDE -MaxParallelActions=4 *> $taskLog
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;log=$taskLog;gameplay_tested=$false;editor_launched=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-receipt.json') -Encoding utf8
    Get-Content -LiteralPath $taskLog -Tail 18 | Where-Object { $_ -notlike '[[]Adaptive Build[]]*' }
    if($taskExit -ne 0){throw "FPSGAMEEditor build failed ($taskExit)"}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
