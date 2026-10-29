$ErrorActionPreference='Stop'
$taskRoot='D:\FPS3D\FPSGAME\SourceAssets\KukriReach20261028'
$taskProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$taskSource='D:\FPS3D\FPSGAME\Source\FPSGAME\Skills\ColdSteelDashAttackModel.cpp'
$taskBuilds=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('dotnet.exe','UnrealBuildTool.exe') -and $_.CommandLine -match 'UnrealBuildTool' })
foreach($taskExisting in $taskBuilds) {
    $taskProcess=Get-Process -Id $taskExisting.ProcessId -ErrorAction SilentlyContinue
    if($taskProcess) { Write-Output "Waiting for existing build process $($taskExisting.ProcessId)."; $taskProcess.WaitForExit() }
}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    $taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))
    if(-not $taskHeld) {throw 'Shared UE batch is occupied; nothing started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue) {throw 'An editor/game is active; leaving it unchanged.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('dotnet.exe','UnrealBuildTool.exe') -and $_.CommandLine -match 'UnrealBuildTool'}) {throw 'Another build started; nothing started.'}
    foreach($taskStage in @('Editor','Game')) {
        $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
        $taskLog=Join-Path $taskRoot "$taskStage-$taskStamp.log"
        $taskConsole=Join-Path $taskRoot "$taskStage-$taskStamp-console.log"
        $taskTarget=if($taskStage -eq 'Editor'){'FPSGAMEEditor'}else{'FPSGAME'}
        $taskHash=(Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash
        & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' $taskTarget Win64 Development "-Project=$taskProject" -NoHotReload -NoHotReloadFromIDE "-Log=$taskLog" *> $taskConsole
        $taskExit=$LASTEXITCODE
        [ordered]@{stage=$taskStage;exit_code=$taskExit;completed=(Get-Date -Format o);log=$taskLog;console=$taskConsole;source=$taskSource;source_sha256=$taskHash;runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot "$taskStage-result.json") -Encoding utf8
        Get-Content -LiteralPath $taskConsole -Tail 12
        if($taskExit -ne 0) {exit $taskExit}
    }
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
