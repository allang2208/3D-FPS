param([int]$WindowSeconds=600)
$ErrorActionPreference='Stop'
$deadline=[DateTime]::UtcNow.AddSeconds($WindowSeconds)
$script=Join-Path $PSScriptRoot 'install_wetness.py'
$runner='D:/FPS3D/FPSGAME/SourceAssets/HighlandClaymoreMeshy20260922/ClovenSurface20261002/install_background.ps1'
$waiting=$false
while([DateTime]::UtcNow -lt $deadline) {
    $owners=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        $_.CommandLine -match 'D:[\\/]FPS3D[\\/]FPSGAME(?:-mp)?[\\/]'
    })
    $blocking=@($owners | Where-Object {
        $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.CommandLine -match 'FPSGAME-mp[\\/]' -or $_.CommandLine -match '(?i)(?:^|\s)-game(?:\s|$)'
    })
    if($blocking) {
        if(-not $waiting){Write-Output 'MELEE_ASSET_QUEUE waiting for the active shared-project process to finish; no processes are stopped.';$waiting=$true}
        foreach($process in $blocking) {
            Wait-Process -Id $process.ProcessId -Timeout 30 -ErrorAction SilentlyContinue
        }
        continue
    }
    try {
        & $runner -Script $script -GateSeconds 60
        exit 0
    } catch {
        # Retry only a refusal before execution; asset script failures keep their
        # partial receipt and are reported without replaying an unknown write.
        if($_.Exception.Message -notmatch 'An existing project commandlet is running|A process sharing Content is active|Asset batch is occupied'){throw}
    }
}
throw 'No safe asset window became available; preparation is saved and no process was stopped.'
