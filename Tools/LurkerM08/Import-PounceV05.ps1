$ErrorActionPreference = 'Stop'
$m08Project = 'D:\FPS3D\FPSGAME'
$m08Output = Join-Path $m08Project 'SourceAssets\Monsters\LurkerM08\PounceV05_20261004'
$m08Deadline = [DateTime]::UtcNow.AddMinutes(20)
while ($true) {
    $m08Busy = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" |
        Where-Object { $_.Name -ne 'dotnet.exe' -or $_.CommandLine -match 'UnrealBuildTool' })
    if ($m08Busy.Count -eq 0) { break }
    [IO.File]::WriteAllText((Join-Path $m08Output 'import_state.txt'), 'Waiting for existing compiler/editor processes. No process stopped.')
    if ([DateTime]::UtcNow -gt $m08Deadline) { throw 'Import slot is still occupied. Exports and script are retained.' }
    Start-Sleep -Seconds 15
}
[IO.File]::WriteAllText((Join-Path $m08Output 'import_state.txt'), 'Importing M08 Pounce V05.')
$m08Arguments = @("$m08Project\FPSGAME.uproject",'-run=pythonscript',"-script=$m08Project\Tools\LurkerM08\install_pounce_v05.py",'-unattended','-nop4','-nosplash','-nosound','-nullrhi','-stdout','-FullStdOutLogOutput','-FORCELOGFLUSH',"-abslog=$m08Output\import_01.log")
$m08Process = Start-Process -FilePath 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' -ArgumentList $m08Arguments -WorkingDirectory $m08Project -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $m08Output 'import_01_stdout.log') -RedirectStandardError (Join-Path $m08Output 'import_01_stderr.log')
$m08Exit = $m08Process.ExitCode
[IO.File]::WriteAllText((Join-Path $m08Output 'import_state.txt'), ('Import exit code: ' + $m08Exit))
Write-Output ('M08 import exit code: ' + $m08Exit)
exit $m08Exit
