$ErrorActionPreference = 'Stop'
$m08Project = 'D:\FPS3D\FPSGAME'
$m08Output = Join-Path $m08Project 'SourceAssets\Monsters\LurkerM08\TraversalV02_20261004'
# Wait for an idle compiler slot, rather than submitting competing WaitMutex builds.
# Does not close editors, stop processes, or communicate with other tasks.
while ($true) {
    $m08Busy = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" |
        Where-Object { $_.Name -ne 'dotnet.exe' -or $_.CommandLine -match 'UnrealBuildTool' })
    if ($m08Busy.Count -eq 0) { break }
    [IO.File]::WriteAllText((Join-Path $m08Output 'build_state.txt'), 'Waiting for existing build/editor processes to finish. No process stopped.')
    Start-Sleep -Seconds 15
}
[IO.File]::WriteAllText((Join-Path $m08Output 'build_state.txt'), 'Building FPSGAMEEditor traversal changes.')
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development "-Project=$m08Project\FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE "-Log=$m08Output\build.log" *> (Join-Path $m08Output 'build_console.log')
$m08Exit = $LASTEXITCODE
[IO.File]::WriteAllText((Join-Path $m08Output 'build_state.txt'), ('Build exit code: ' + $m08Exit))
exit $m08Exit
