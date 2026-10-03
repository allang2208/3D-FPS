$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$trashRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'trash/m16-retired-20260920'))
$plan = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'archive_plan.json') -Raw | ConvertFrom-Json
$rows = [Collections.Generic.List[object]]::new()
foreach ($entry in $plan) {
    $source = [IO.Path]::GetFullPath($entry.source)
    $destination = [IO.Path]::GetFullPath($entry.destination)
    $relative = [IO.Path]::GetRelativePath($projectRoot, $source).Replace('\','/')
    if (-not $source.StartsWith($projectRoot + '\',[StringComparison]::OrdinalIgnoreCase) -or
        -not ($relative -match '^SourceAssets/M16[^/]+/' -or $relative -eq 'Docs/Weapons/m16a2-empty-reload-short-press-20260920.md') -or
        -not $destination.StartsWith($trashRoot + '\',[StringComparison]::OrdinalIgnoreCase)) {
        throw "Archive path outside this task: $source -> $destination"
    }
    if (Test-Path -LiteralPath $destination) { throw "Archive destination already exists: $destination" }
    $sourceItem = Get-Item -LiteralPath $source
    $files = if ($sourceItem.PSIsContainer) { @(Get-ChildItem -LiteralPath $source -File -Recurse) } else { @($sourceItem) }
    foreach ($file in $files) {
        $suffix = if ($sourceItem.PSIsContainer) { [IO.Path]::GetRelativePath($source,$file.FullName) } else { '' }
        $targetFile = if ($suffix) { Join-Path $destination $suffix } else { $destination }
        $rows.Add([pscustomobject]@{source=[IO.Path]::GetRelativePath($projectRoot,$file.FullName).Replace('\','/');destination=[IO.Path]::GetRelativePath($projectRoot,$targetFile).Replace('\','/');bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant();reason=$entry.reason;retained=$entry.retained})
    }
    [IO.Directory]::CreateDirectory((Split-Path -Parent $destination)) | Out-Null
    Move-Item -LiteralPath $source -Destination $destination
    foreach ($row in $rows | Where-Object { $_.destination -eq [IO.Path]::GetRelativePath($projectRoot,$destination).Replace('\','/') -or $_.destination.StartsWith([IO.Path]::GetRelativePath($projectRoot,$destination).Replace('\','/')+'/') }) {
        $target = Join-Path $projectRoot $row.destination
        if ((Get-Item -LiteralPath $target).Length -ne $row.bytes -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $row.sha256) { throw "Archive verification failed: $target" }
    }
    $rows | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'archive-sources.json') -Encoding utf8
}
Write-Output "Archived $($rows.Count) source files; SHA-256 copies match."
