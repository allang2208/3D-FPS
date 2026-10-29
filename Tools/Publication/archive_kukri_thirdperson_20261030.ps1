$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$archiveRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot 'trash\KukriThirdPerson20261030'))
$plan = Get-Content -LiteralPath (Join-Path $projectRoot 'Docs\Publication\KukriThirdPerson20261030\archive-manifest.json') -Raw | ConvertFrom-Json
$receipts = @()
foreach ($item in $plan.entries) {
    $source = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $item.original))
    $dest = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $item.destination))
    if (-not $source.StartsWith($projectRoot + '\SourceAssets\', [System.StringComparison]::OrdinalIgnoreCase)) { throw "Source out of scope: $source" }
    if (-not $dest.StartsWith($archiveRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) { throw "Destination out of scope: $dest" }
    if (Test-Path -LiteralPath $source) {
        $resolved = (Resolve-Path -LiteralPath $source).ProviderPath
        if (-not ($resolved.StartsWith($projectRoot + '\SourceAssets\', [System.StringComparison]::OrdinalIgnoreCase) -or $resolved.StartsWith('F:\FPSGAMEData\SourceAssets\', [System.StringComparison]::OrdinalIgnoreCase))) { throw "Resolved path out of scope: $resolved" }
        if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) { throw "Source changed: $source" }
        if (Test-Path -LiteralPath $dest) { throw "Destination exists: $dest" }
        [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($dest)) | Out-Null
        Move-Item -LiteralPath $source -Destination $dest
    }
    if ((Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) { throw "Archive hash mismatch: $dest" }
    $item | Add-Member -NotePropertyName verified_after_move -NotePropertyValue $true -Force
    $receipts += $item
}
$report = [ordered]@{ files=$receipts.Count; bytes=$plan.bytes; entries=$receipts; destructive_delete=$false }
$json = $report | ConvertTo-Json -Depth 8
[System.IO.Directory]::CreateDirectory($archiveRoot) | Out-Null
[System.IO.File]::WriteAllText((Join-Path $archiveRoot 'manifest.json'), $json, [System.Text.UTF8Encoding]::new($false))
$publicationRoot = Join-Path $projectRoot 'Docs\Publication\KukriThirdPerson20261030'
[System.IO.Directory]::CreateDirectory($publicationRoot) | Out-Null
[System.IO.File]::WriteAllText((Join-Path $publicationRoot 'archive-manifest.json'), $json, [System.Text.UTF8Encoding]::new($false))
Write-Output "Archived $($receipts.Count) files; SHA256 verified after every move."
