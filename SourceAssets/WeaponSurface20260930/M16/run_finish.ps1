param()
$ErrorActionPreference='Stop'
# Both project variants share Content. The online editor blocked the M16 weather
# table save; defer while that editor or a shared-content game owns the packages.
$sharedOwners=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
    $_.CommandLine -match 'D:[\\/]FPS3D[\\/]FPSGAME-mp[\\/]' -or (
        $_.CommandLine -match 'D:[\\/]FPS3D[\\/]FPSGAME[\\/]' -and $_.CommandLine -match '(?i)(?:^|\s)-game(?:\s|$)'
    )
})
if($sharedOwners){throw ('Shared-content editor or game still active: '+(($sharedOwners.ProcessId)-join ', '))}
$runner=Join-Path $PSScriptRoot '../run_ue.ps1'
& $runner -Script 'M16/Refine01/apply_finish.py'
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
