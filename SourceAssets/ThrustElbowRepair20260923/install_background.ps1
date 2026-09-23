$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$engineCmd = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$batchGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$gateHeld = $false
try {
    try { $gateHeld = $batchGate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] { $gateHeld = $true }
    if (-not $gateHeld) { throw 'The UE integration batch gate is still busy.' }
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
        throw 'An editor is open. Use the existing MCP batch bridge for this import.'
    }
    & $engineCmd "$projectRoot\FPSGAME.uproject" -run=pythonscript `
        "-script=$PSScriptRoot\install_repair.py" -unattended -nop4 -nosplash -nosound -NoLiveCoding -multiprocess `
        -RenderOffscreen -AllowCommandletRendering `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
        "-abslog=$PSScriptRoot\install.log" *> "$PSScriptRoot\install-console.log"
    $resultCode = $LASTEXITCODE
} finally {
    if ($gateHeld) { $batchGate.ReleaseMutex() }
    $batchGate.Dispose()
}
exit $resultCode
