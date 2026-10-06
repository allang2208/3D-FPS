$ErrorActionPreference = 'Stop'
$opticProject = 'D:/FPS3D/FPSGAME'
$opticOutput = "$opticProject/SourceAssets/G18HolographicTransparency20261005"
$opticGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$opticHeld = $false
try {
    try { $opticHeld = $opticGate.WaitOne(60000) } catch [Threading.AbandonedMutexException] { $opticHeld = $true }
    if (-not $opticHeld) { throw 'The asset batch is busy; no commandlet was started.' }
    $opticProcesses = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if ($opticProcesses.Count -gt 0) { throw 'An Unreal editor or commandlet is running; preserve it and use the existing editor bridge when applicable.' }
    $opticArgs = @("$opticProject/FPSGAME.uproject", '-run=pythonscript', "-script=$opticOutput/apply_materials.py",
        '-NullRHI', '-Multiprocess', '-unattended', '-nop4', '-nosplash', '-nosound', '-stdout', '-FullStdOutLogOutput',
        "-abslog=$opticOutput/save-assets.log")
    $opticProcess = Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        -ArgumentList $opticArgs -WorkingDirectory $opticProject -WindowStyle Hidden -PassThru -Wait `
        -RedirectStandardOutput "$opticOutput/save-console.log" -RedirectStandardError "$opticOutput/save-stderr.log"
    if ($opticProcess.ExitCode -ne 0) { throw "G18 material save commandlet exited $($opticProcess.ExitCode); see save-assets.log." }
    Write-Output 'G18 material commandlet completed. No runtime or visual tests were run.'
} finally {
    if ($opticHeld) { $opticGate.ReleaseMutex() }
    $opticGate.Dispose()
}
