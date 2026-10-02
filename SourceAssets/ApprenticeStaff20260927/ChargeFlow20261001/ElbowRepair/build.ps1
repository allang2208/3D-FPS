$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME'
$taskLogDirectory=$PSScriptRoot
$taskBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
# Wait for the currently running UBT, then build this project's two targets.
# No editor, game, automation test or cross-task message is started.
while (@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool'}).Count -gt 0) {
    Start-Sleep -Seconds 5
}
foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
    if($taskTarget -eq 'FPSGAMEEditor') {
        $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape('FPSGAME.uproject')
        })
        if($taskEditors.Count -gt 0){throw 'Primary FPSGAME editor opened; retain editor state and do not overwrite its module.'}
    }
    $taskLog=Join-Path $taskLogDirectory ($taskTarget+'-build.log')
    Write-Output "Building $taskTarget in background."
    & $taskBuild $taskTarget Win64 Development "-Project=$taskProject\FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE "-Log=$taskLog"
    if($LASTEXITCODE -ne 0){throw "$taskTarget build failed: $taskLog"}
    Write-Output "$taskTarget build succeeded."
}
