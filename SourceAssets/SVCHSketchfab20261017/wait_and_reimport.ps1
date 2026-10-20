# Wait for Play-In-Editor to stop, then re-import the SVCh viewmodel through the
# editor bridge (the running editor holds the packages, so an offline commandlet
# cannot save over them) and re-shoot the inventory icon.
#
# Everything goes through the project's batch mutex; nothing is forced. The
# bridge answers on stderr while the editor is busy, so stderr is inspected
# rather than treated as a failure.
param(
    [int]$TimeoutSeconds = 2700,
    [int]$PollSeconds = 20
)
$case = 'D:\FPS3D\FPSGAME\SourceAssets\SVCHSketchfab20261017'
$bridge = 'D:\FPS3D\FPSGAME\Tools\AssetPipeline\mcp_call_codex.ps1'
$state = Join-Path $case 'check_state.py'
$import = Join-Path $case 'import_assets.py'
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)

function Invoke-Bridge([string]$script) {
    $all = & powershell -NoProfile -ExecutionPolicy Bypass -File $bridge -PythonScript $script 2>&1
    return (($all | ForEach-Object { [string]$_ }) -join "`n")
}

Write-Output "waiting for PIE to stop (timeout ${TimeoutSeconds}s)"
$ready = $false
while ((Get-Date) -lt $deadline) {
    $text = Invoke-Bridge $state
    if ($text -match '"pie_running":\s*false') { $ready = $true; break }
    if ($text -match 'success=False' -and $text -notmatch 'PIE is running') {
        Write-Output 'state probe reported an unexpected failure; retrying'
    }
    Start-Sleep -Seconds $PollSeconds
}
if (-not $ready) { Write-Output 'TIMEOUT_WAITING_FOR_PIE'; exit 3 }

Write-Output 'PIE stopped; importing through the editor bridge'
$text = Invoke-Bridge $import
Write-Output $text
if ($text -notmatch 'SVCH_IMPORT') { Write-Output 'IMPORT_FAILED'; exit 4 }
Write-Output 'IMPORT_OK'

Start-Sleep -Seconds 3
Write-Output 're-shooting the inventory icon'
$icon = & powershell -NoProfile -ExecutionPolicy Bypass -File 'D:\FPS3D\FPSGAME\Tools\UI\build_weapon_catalog_icons.ps1' -Definitions ue_svch 2>&1
$icon | Select-Object -Last 2 | ForEach-Object { Write-Output ([string]$_) }
Write-Output 'DONE'
