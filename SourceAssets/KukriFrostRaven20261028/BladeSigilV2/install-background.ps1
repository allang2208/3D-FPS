$ErrorActionPreference = 'Stop'
$sigilProject = 'D:\FPS3D\FPSGAME\FPSGAME.uproject'
$sigilGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$sigilGateHeld = $false
$sigilPreviousSDK = $env:UE_SKIP_UBT_SDK_SETUP
try {
    try { $sigilGateHeld = $sigilGate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] {
        $sigilGateHeld = $true
        throw 'Previous UE batch outcome is unknown; preserve project state.'
    }
    if (-not $sigilGateHeld) { throw 'UE authoring batch is busy; no commandlet was started.' }
    $sigilEditors = @(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'UnrealEditor-Cmd.exe'" |
        Where-Object { $_.CommandLine -and $_.CommandLine.Replace('/', '\').Contains($sigilProject) })
    if ($sigilEditors.Count) { throw 'A project editor/commandlet is active; preserve its asset batch.' }
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    $sigilArguments = @(
        "`"$sigilProject`"", '-run=pythonscript', "-script=`"$PSScriptRoot\install_surfaces.py`"",
        '-unattended', '-nosplash', '-d3d12', '-AllowCommandletRendering', '-nosound', '-NoLiveCoding',
        "-abslog=`"$PSScriptRoot\install-commandlet.log`""
    )
    $sigilProcess = Start-Process -FilePath 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
        -ArgumentList $sigilArguments -WindowStyle Hidden -PassThru -Wait `
        -RedirectStandardOutput (Join-Path $PSScriptRoot 'install-console.log') `
        -RedirectStandardError (Join-Path $PSScriptRoot 'install-stderr.log')
    $sigilExit = $sigilProcess.ExitCode
} finally {
    if ($null -eq $sigilPreviousSDK) { Remove-Item Env:UE_SKIP_UBT_SDK_SETUP -ErrorAction SilentlyContinue }
    else { $env:UE_SKIP_UBT_SDK_SETUP = $sigilPreviousSDK }
    if ($sigilGateHeld) { $sigilGate.ReleaseMutex() }
    $sigilGate.Dispose()
}
Write-Output "Fine blade sigil commandlet exit: $sigilExit"
exit $sigilExit
