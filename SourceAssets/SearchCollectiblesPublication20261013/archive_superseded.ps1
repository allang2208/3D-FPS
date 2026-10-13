$ErrorActionPreference='Stop'
$archiveRoot=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME')
$archiveTarget=[IO.Path]::GetFullPath((Join-Path $archiveRoot 'trash/search-collectibles-20261013'))
$archiveManifest=Join-Path $archiveRoot 'Docs/Publication/SearchCollectibles20261013/archive-manifest.json'
$archivePlan=Get-Content -LiteralPath $archiveManifest -Raw | ConvertFrom-Json
if($archivePlan.status -ne 'planned'){throw 'Archive manifest already executed or changed'}
if(Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'UnrealEditor*' -and $_.CommandLine -like '*ServerReferenceRemodel20261013*' }) {
    throw 'Retired import host is still running; preserve its files.'
}
foreach($archiveFile in $archivePlan.files) {
    $archiveSource=[IO.Path]::GetFullPath((Join-Path $archiveRoot $archiveFile.source))
    $archiveDestination=[IO.Path]::GetFullPath((Join-Path $archiveRoot $archiveFile.destination))
    if(-not $archiveSource.StartsWith($archiveRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or
       -not $archiveDestination.StartsWith($archiveTarget+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Archive path escaped its declared root'}
    if(Test-Path -LiteralPath $archiveDestination){throw "Refusing to replace $archiveDestination"}
    if((Get-FileHash -LiteralPath $archiveSource -Algorithm SHA256).Hash -ne $archiveFile.sha256){throw "Source changed: $archiveSource"}
}
foreach($archiveFile in $archivePlan.files) {
    $archiveSource=Join-Path $archiveRoot $archiveFile.source
    $archiveDestination=Join-Path $archiveRoot $archiveFile.destination
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $archiveDestination) | Out-Null
    Move-Item -LiteralPath $archiveSource -Destination $archiveDestination
    if((Get-FileHash -LiteralPath $archiveDestination -Algorithm SHA256).Hash -ne $archiveFile.sha256){throw "Archive readback mismatch: $archiveDestination"}
}
$archivePlan.status='moved_and_sha256_verified'
$archivePlan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $archiveManifest -Encoding utf8
Copy-Item -LiteralPath $archiveManifest -Destination (Join-Path $archiveTarget 'archive-manifest.json')
Write-Output "ARCHIVED_FILES=$($archivePlan.file_count) BYTES=$($archivePlan.total_bytes)"
