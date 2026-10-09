[CmdletBinding()]
param([switch]$RestorePreviousVersion)
$ErrorActionPreference='Stop'
if (-not $RestorePreviousVersion) { throw 'To restore the old version, rerun with -RestorePreviousVersion. Current map will be preserved in this archive.' }
$project='D:\FPS3D\FPSGAME'
$archive=(Resolve-Path -LiteralPath $PSScriptRoot).Path
if (-not $archive.StartsWith(($project+'\trash\PowerTheme20261004-ReplacedByRefineV2-'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Run only from the recorded recovery directory' }
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try { $held=$gate.WaitOne(0) } catch [Threading.AbandonedMutexException] { $held=$true }
    if (-not $held) { throw 'UE batch active; nothing restored' }
    if (Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME' }) { throw 'Preserve running editor; close it normally before restoring' }
    $moves=Get-Content -LiteralPath (Join-Path $archive 'moves.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $canonical=$project+'\Content\GameMaps\Design\L_PowerTheme20261004_Subject.umap'
    foreach ($m in $moves) {
        if ($m.archive -match '\\Staging\\|\\FailedPublication\\') { continue }
        $dest=[IO.Path]::GetFullPath($m.source)
        if (-not $dest.StartsWith(($project+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected restore path' }
        if ((Test-Path -LiteralPath $dest) -and $dest -ne $canonical) { throw ('Restore target already exists: '+$dest) }
        if ($m.kind -eq 'file' -and (Get-FileHash -LiteralPath $m.archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $m.sha256) { throw 'Recovery file hash mismatch' }
    }
    if (Test-Path -LiteralPath $canonical) {
        $saved=Join-Path $archive ('NewVersionBeforeRestore-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.umap')
        Move-Item -LiteralPath $canonical -Destination $saved
    }
    foreach ($m in $moves) {
        if ($m.archive -match '\\Staging\\|\\FailedPublication\\') { continue }
        New-Item -ItemType Directory -Force -Path (Split-Path $m.source -Parent) | Out-Null
        Copy-Item -LiteralPath $m.archive -Destination $m.source -Recurse
    }
    Write-Output 'Old scene restored. Recovery archive and new RefineV2 assets retained. No game or editor started.'
} finally { if ($held) { $gate.ReleaseMutex() };$gate.Dispose() }
