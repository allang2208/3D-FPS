$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while(-not $taskHeld){
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))}
        catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    $taskEditor=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor' -and ((-not $_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')})
    if($taskEditor.Count -gt 0){throw 'Preserve the running editor/commandlet. No concurrent audit started.'}
    while(@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool.dll'}).Count -gt 0){Start-Sleep -Seconds 5}
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskReport=Join-Path $PSScriptRoot ('heavy-formula-'+$taskStamp+'.json')
    $taskLog=Join-Path $PSScriptRoot ('audit-'+$taskStamp+'.log')
    $taskConsole=Join-Path $PSScriptRoot ('audit-'+$taskStamp+'-console.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=WarhammerModificationAudit -HeavyFormula "-Out=$taskReport" -nullrhi -unattended -nop4 -nosplash -nosound -NoLiveCoding -stdout -FullStdOutLogOutput "-abslog=$taskLog" *> $taskConsole
    $taskCode=$LASTEXITCODE
    [ordered]@{exit_code=$taskCode;report=$taskReport;engine_log=$taskLog;finished=(Get-Date).ToString('o');gameplay_started=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PSScriptRoot ('audit-'+$taskStamp+'-receipt.json')) -Encoding utf8
    Get-Content -LiteralPath $taskConsole -Tail 18
    exit $taskCode
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
