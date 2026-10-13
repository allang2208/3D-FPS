$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskMutex=New-Object System.Threading.Mutex($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while(-not $taskHeld) {
        try {$taskHeld=$taskMutex.WaitOne(1000)} catch [System.Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    do {
        $taskBuilders=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*' })
        if($taskBuilders.Count) {$taskBuilders | ForEach-Object { Wait-Process -Id $_.ProcessId -Timeout 40 -ErrorAction SilentlyContinue }}
    } while($taskBuilders.Count)
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Existing GUI editor preserved; headless checks deferred.'}
    $taskLog=Join-Path $taskRoot 'Receipts/automation.log'
    $taskReport=Join-Path $taskRoot 'Receipts/Automation'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '/Engine/Maps/Entry' '-unattended' '-NullRHI' '-nosplash' '-nosound' '-nop4' '-NoLoadStartupPackages' '-ExecCmds=Automation RunTests FPSGAME.SceneSearch' '-TestExit=Automation Test Queue Empty' "-ReportExportPath=$taskReport" "-abslog=$taskLog" *> (Join-Path $taskRoot 'Receipts/automation-stdout.log')
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;log=$taskLog;report=$taskReport;mode='headless_memory_only';player_save_slots_used=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'Receipts/code-check-run.json') -Encoding utf8
    Write-Output "SCENE_SEARCH_CHECK_EXIT=$taskExit"
    exit $taskExit
} finally {
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
