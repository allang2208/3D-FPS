$ErrorActionPreference = 'Stop'
$taskGate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld = $false
try {
    try { $taskHeld = $taskGate.WaitOne([TimeSpan]::FromSeconds(600)) }
    catch [Threading.AbandonedMutexException] { $taskHeld = $true }
    if (-not $taskHeld) { throw 'Asset batch remains busy; current work preserved.' }
    if (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") { throw 'Use the running editor bridge; preserve loaded packages.' }
    if (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'") { throw 'Another background authoring process exists; preserve its packages.' }
    $taskAsset='D:/FPS3D/FPSGAME/Content/Weapons/CommonHammerSeats20261107/ConicalSeatV1/head_mount_conical_seat.uasset'
    $taskBefore=Join-Path $PSScriptRoot 'Before/head_mount_conical_seat.uasset'
    if (Test-Path -LiteralPath $taskBefore) { throw 'Before-copy already exists; preserve original receipt.' }
    Copy-Item -LiteralPath $taskAsset -Destination $taskBefore
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript ('-script=' + $PSScriptRoot + '/import_icon.py') -unattended -nop4 -nosplash -NoSound -NoLiveCoding -AllowCommandletRendering -RenderOffscreen -d3d12 -sm6 -stdout -FullStdOutLogOutput ('-abslog=' + $PSScriptRoot + '/import.log') *> ($PSScriptRoot + '/import-console.log')
    exit $LASTEXITCODE
} finally {
    if ($taskHeld) { $taskGate.ReleaseMutex() }
    $taskGate.Dispose()
}
