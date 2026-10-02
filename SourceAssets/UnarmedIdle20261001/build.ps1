$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME'
$taskBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
# Background compilation only. Do not launch or close an editor or game.
while (@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool'}).Count -gt 0) {
    Start-Sleep -Seconds 5
}
$taskTargets=@('FPSGAME')
$taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
    [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape('FPSGAME.uproject')
})
if($taskEditors.Count -eq 0){$taskTargets+= 'FPSGAMEEditor'}
else {Write-Output 'FPSGAMEEditor build deferred: the primary editor is open; preserve its loaded module.'}
foreach($taskTarget in $taskTargets) {
    if($taskTarget -eq 'FPSGAMEEditor') {
        $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape('FPSGAME.uproject')
        })
        if($taskEditors.Count -gt 0){throw 'Primary editor opened; preserve the loaded module and defer FPSGAMEEditor.'}
    }
    $taskLog=Join-Path $PSScriptRoot ($taskTarget+'-build.log')
    Write-Output "Building $taskTarget in background."
    & $taskBuild $taskTarget Win64 Development "-Project=$taskProject\FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE "-Log=$taskLog"
    if($LASTEXITCODE -ne 0){throw "$taskTarget build failed: $taskLog"}
    Write-Output "$taskTarget build succeeded."
}
