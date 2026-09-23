param([string]$RunName = 'assets-1')
$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$engineCommand = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$receiptRoot = Join-Path $PSScriptRoot 'Receipts'
[IO.Directory]::CreateDirectory($receiptRoot) | Out-Null
# Same batch mutex as mcp_call_codex.ps1; do not overlap a live editor operation.
$productionGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$gateHeld = $false
try {
    try { $gateHeld = $productionGate.WaitOne(300000) }
    catch [Threading.AbandonedMutexException] { $gateHeld = $true }
    if (-not $gateHeld) { throw 'Production batch lock timeout; nothing changed.' }
    $activeProject = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" |
        Where-Object { $_.CommandLine -like '*FPSGAME.uproject*' }
    if ($activeProject) { throw 'FPSGAME already has an engine process; preserve its loaded assets.' }
    $arguments = @(
        ('"' + $projectRoot + '/FPSGAME.uproject"'), '-run=pythonscript',
        ('-script="' + (Join-Path $PSScriptRoot 'background_assets.py') + '"'),
        '-Unattended', '-NullRHI', '-NoSplash', '-NoSound', '-NoLiveCoding',
        ('-abslog="' + (Join-Path $receiptRoot ($RunName + '-engine.log')) + '"'), '-stdout', '-FullStdOutLogOutput'
    )
    $worker = Start-Process -FilePath $engineCommand -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -Wait -PassThru `
        -RedirectStandardOutput (Join-Path $receiptRoot ($RunName + '-stdout.log')) `
        -RedirectStandardError (Join-Path $receiptRoot ($RunName + '-stderr.log'))
    $resultCode = $worker.ExitCode
    Write-Output ('Background asset production exit code: ' + $resultCode)
}
finally {
    if ($gateHeld) { $productionGate.ReleaseMutex() }
    $productionGate.Dispose()
}
exit $resultCode
