$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject='D:\FPS3D\FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskResults=@{}
try {
    while (-not $taskHeld) {try {$taskHeld=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}}
    while (Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME'}) {Start-Sleep -Seconds 5}
    if (Get-CimInstance Win32_Process | Where-Object {($_.Name -in @('UnrealEditor.exe','FPSGAME.exe')) -and $_.CommandLine -match 'FPSGAME'}) {throw 'Preserve running editor/game; native binaries are occupied.'}
    foreach ($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
        $taskLog=Join-Path $taskRoot ("Receipts/$taskTarget-build.log")
        & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' $taskTarget Win64 Development "-project=$taskProject\FPSGAME.uproject" -NoHotReloadFromIDE -WaitMutex *> $taskLog
        $taskResults[$taskTarget]=$LASTEXITCODE
        Write-Output "$taskTarget BUILD_EXIT=$LASTEXITCODE"
        if ($LASTEXITCODE -ne 0) {throw "Native build failed: $taskTarget"}
    }
    @{stage='binaries_saved';targets=$taskResults;tests_run=$false;game_run=$false} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskRoot 'Receipts/native-build.json') -Encoding UTF8
} catch {
    @{stage='build_incomplete';targets=$taskResults;reason=$_.Exception.Message;tests_run=$false} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskRoot 'Receipts/native-build.json') -Encoding UTF8
    throw
} finally {if ($taskHeld) {$taskGate.ReleaseMutex()};$taskGate.Dispose()}
