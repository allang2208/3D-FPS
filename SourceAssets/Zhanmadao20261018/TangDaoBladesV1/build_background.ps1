param([string]$Attempt='01',[string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if (-not $taskHeld) {throw 'Build queue timed out.'}
    foreach ($taskTarget in $Targets) {
        $taskDeadline=(Get-Date).AddMinutes(30)
        while ($true) {
            $taskEditors=Get-Process UnrealEditor,UnrealEditor-Cmd,UnrealBuildTool -ErrorAction SilentlyContinue
            $taskUbt=Get-CimInstance Win32_Process -Filter "Name = 'dotnet.exe'" | Where-Object { $_.CommandLine -like '*UnrealBuildTool.dll*' }
            if (-not $taskEditors -and -not $taskUbt) {break}
            if ((Get-Date) -gt $taskDeadline) {throw 'A UE/build process is still active; preserved it.'}
            Start-Sleep -Seconds 10
        }
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBA -NoUBTMakefiles -MaxParallelActions=4 "-Log=$taskRoot/build-$taskTarget-$Attempt.log" *> "$taskRoot/build-$taskTarget-console-$Attempt.log"
        $taskExit=$LASTEXITCODE
        @{target=$taskTarget;exit_code=$taskExit;finished=(Get-Date).ToString('o');game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/build-$taskTarget-receipt-$Attempt.json" -Encoding UTF8
        if ($taskExit -ne 0) {throw "$taskTarget build failed ($taskExit)."}
    }
    Write-Output ('ZHANMADAO_BUILD_SAVED: '+($Targets -join ', '))
} finally {
    if ($taskHeld) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
