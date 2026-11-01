$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$manifestPath = Join-Path $projectRoot 'Docs/Publication/M24_20261101/archive-manifest.json'
$receiptPath = Join-Path $projectRoot 'Docs/Publication/M24_20261101/archive-receipt.json'
$archiveRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'trash/m24-retired-20261101'))
$rows = (Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json).files
$receipts = @()
foreach ($row in $rows) {
    $source = [IO.Path]::GetFullPath((Join-Path $projectRoot $row.source))
    $destination = [IO.Path]::GetFullPath((Join-Path $projectRoot $row.destination))
    $rel = $row.source -replace '\\','/'
    if ($rel -notmatch '^SourceAssets/(M24[^/]+|SkeletonSniperStock20261031)/' -or
        -not $source.StartsWith($projectRoot + '\',[StringComparison]::OrdinalIgnoreCase) -or
        -not $destination.StartsWith($archiveRoot + '\',[StringComparison]::OrdinalIgnoreCase)) { throw "Outside owned archive boundary: $rel" }
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing source: $rel" }
    if ((Get-Item -LiteralPath $source).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse source: $rel" }
    $parent = (Get-Item -LiteralPath $source).Directory
    while ($parent.FullName -ne $projectRoot) {
        if ($parent.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse ancestor: $rel" }
        $parent = $parent.Parent
        if ($null -eq $parent) { throw "Unresolved boundary: $rel" }
    }
    if (Test-Path -LiteralPath $destination) { throw "Destination exists: $destination" }
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw "Source changed: $rel" }
}
foreach ($row in $rows) {
    $source = Join-Path $projectRoot $row.source
    $destination = Join-Path $projectRoot $row.destination
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($destination)) -Force | Out-Null
    Move-Item -LiteralPath $source -Destination $destination
    $hash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $row.sha256 -or (Test-Path -LiteralPath $source)) { throw "Archive readback failed: $($row.source)" }
    $receipts += [ordered]@{ source=$row.source; destination=$row.destination; bytes=$row.bytes; sha256=$hash; moved=$true }
    [ordered]@{ complete=$false; files=$receipts } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
}
[ordered]@{ complete=$true; count=$receipts.Count; bytes=($receipts | Measure-Object -Property bytes -Sum).Sum; files=$receipts } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
Write-Output "Archived $($receipts.Count) files; SHA-256 readback matched."
