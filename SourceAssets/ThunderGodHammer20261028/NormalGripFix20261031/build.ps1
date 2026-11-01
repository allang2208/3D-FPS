$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    for ($taskAttempt=0; $taskAttempt -lt 20 -and -not $taskHeld; $taskAttempt++) {
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if (-not $taskHeld) {Write-Output 'Waiting for existing project batch.'}
    }
    if (-not $taskHeld) {throw 'Project batch busy; no build started.'}
    if (@(Get-Process UnrealEditor -ErrorAction SilentlyContinue).Count -gt 0) {throw 'Editor running; preserve loaded modules.'}
    if (@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.dll')}).Count -gt 0) {throw 'Another build/import is active; preserve it.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "$taskRoot/FPSGAME.uproject" -NoHotReloadFromIDE *> (Join-Path $PSScriptRoot 'build.log')
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;target='FPSGAMEEditor Win64 Development';runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
    Write-Output "Build exit=$taskExit"
    exit $taskExit
} finally {if ($taskHeld) {$taskGate.ReleaseMutex()};$taskGate.Dispose()}
