$ErrorActionPreference = 'Stop'
$m08Project = 'D:\FPS3D\FPSGAME'
$m08Output = Join-Path $m08Project 'SourceAssets\Monsters\LurkerM08\AirWarningV11_20261005'
$m08Deadline = [DateTime]::UtcNow.AddMinutes(20)
while ($true) {
    $m08Busy = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" |
        Where-Object { $_.Name -ne 'dotnet.exe' -or $_.CommandLine -match 'UnrealBuildTool' })
    if ($m08Busy.Count -eq 0) { break }
    [IO.File]::WriteAllText((Join-Path $m08Output 'build_state.txt'), 'Waiting for existing compiler/editor processes. No process stopped.')
    if ([DateTime]::UtcNow -gt $m08Deadline) { throw 'Build slot is still occupied. Air warning source changes are retained.' }
    Start-Sleep -Seconds 15
}
[IO.File]::WriteAllText((Join-Path $m08Output 'build_state.txt'), 'Building FPSGAMEEditor M08 Air Warning V11.')
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development "-Project=$m08Project\FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE "-Log=$m08Output\build_01.log" *> (Join-Path $m08Output 'build_console_01.log')
$m08Exit = $LASTEXITCODE
[IO.File]::WriteAllText((Join-Path $m08Output 'build_state.txt'), ('Build exit code: ' + $m08Exit))
exit $m08Exit
