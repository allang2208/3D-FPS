$ErrorActionPreference='Stop'
$svchRoot=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME')
$svchPrefix=$svchRoot+[IO.Path]::DirectorySeparatorChar
$svchTrash=[IO.Path]::GetFullPath((Join-Path $svchRoot 'trash/svch-retired-20261020'))+[IO.Path]::DirectorySeparatorChar
$svchManifest=Join-Path $svchRoot 'Docs/Publication/SVCH20261020/archive-manifest.json'
$svchRows=Get-Content -LiteralPath $svchManifest -Raw | ConvertFrom-Json
foreach($row in $svchRows) {
    $source=[IO.Path]::GetFullPath((Join-Path $svchRoot $row.source))
    $destination=[IO.Path]::GetFullPath((Join-Path $svchRoot $row.destination))
    if(!$source.StartsWith($svchPrefix,[StringComparison]::OrdinalIgnoreCase) -or
       !$destination.StartsWith($svchTrash,[StringComparison]::OrdinalIgnoreCase)) {throw 'Archive path escapes intended workspace'}
    if(!(Test-Path -LiteralPath $source -PathType Leaf)) {
        if((Test-Path -LiteralPath $destination -PathType Leaf) -and
           (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -eq $row.sha256) {continue}
        throw "Missing archive source: $($row.source)"
    }
    if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $row.sha256) {throw "Source changed: $($row.source)"}
    if(Test-Path -LiteralPath $destination) {throw "Destination already exists: $($row.destination)"}
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($destination)) -Force | Out-Null
    Move-Item -LiteralPath $source -Destination $destination
    if((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash -ne $row.sha256) {throw "Archive hash mismatch: $($row.destination)"}
}
@{complete=$true;files=$svchRows.Count;bytes=($svchRows|Measure-Object -Property bytes -Sum).Sum;
  completed_utc=[DateTime]::UtcNow.ToString('o');manifest='Docs/Publication/SVCH20261020/archive-manifest.json'} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $svchRoot 'Docs/Publication/SVCH20261020/archive-receipt.json') -Encoding utf8
Write-Output "SVCH_ARCHIVE_COMPLETE files=$($svchRows.Count)"
