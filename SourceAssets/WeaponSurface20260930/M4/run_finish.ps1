param()
$ErrorActionPreference='Stop'
# Both project variants use the same physical Content directory. A live online
# game held the M4 package during the first save, so defer this batch until idle.
$sharedGames=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {
    $_.CommandLine -match 'D:[\\/]FPS3D[\\/]FPSGAME(?:-mp)?[\\/]' -and $_.CommandLine -match '(?i)(?:^|\s)-game(?:\s|$)'
})
if($sharedGames){throw ('Shared-content game instances still active: '+(($sharedGames.ProcessId)-join ', '))}
$runner=Join-Path $PSScriptRoot '../run_ue.ps1'
& $runner -Script 'M4/Refine01/apply_finish.py'
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
