$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath('D:/FPS3D/FPSGAME').TrimEnd('\')
$archiveRoot = [IO.Path]::GetFullPath((Join-Path $workspace 'trash/outfit-closeout-20260930')).TrimEnd('\')
$plan = Get-Content -LiteralPath (Join-Path $workspace 'SourceAssets/OutfitCloseout20260930/archive-plan.json') -Raw | ConvertFrom-Json
if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'An editor owns assets; retain the archive plan and retry after the process exits.' }
# Resolve and check every final path before any move. Move files within this workspace only.
foreach ($item in $plan.items) {
    $source = [IO.Path]::GetFullPath((Join-Path $workspace $item.source))
    $target = [IO.Path]::GetFullPath((Join-Path $workspace $item.target))
    if (!$source.StartsWith($workspace+'\',[StringComparison]::OrdinalIgnoreCase) -or !$target.StartsWith($archiveRoot+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Archive path escaped workspace.' }
    if (!(Test-Path -LiteralPath $source -PathType Leaf) -or (Test-Path -LiteralPath $target)) { throw "Source missing or archive occupied: $source" }
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) { throw "Source changed: $source" }
    if ([IO.Path]::GetExtension($source) -eq '.uasset') {
        $assetHandle = [IO.File]::Open($source,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::None)
        $assetHandle.Dispose()
    }
}
$manifestDir = Join-Path $workspace 'Docs/Publication/OutfitCloseout20260930'
New-Item -ItemType Directory -Force -Path $manifestDir | Out-Null
$manifestPath = Join-Path $manifestDir 'archive-manifest.json'
$moved = @()
foreach ($item in $plan.items) {
    $source = [IO.Path]::GetFullPath((Join-Path $workspace $item.source))
    $target = [IO.Path]::GetFullPath((Join-Path $workspace $item.target))
    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($target)) | Out-Null
    Move-Item -LiteralPath $source -Destination $target
    $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($hash -ne $item.sha256) { throw "Archive digest mismatch: $target" }
    $item | Add-Member -NotePropertyName archived_sha256 -NotePropertyValue $hash
    $moved += $item
    [IO.File]::WriteAllText($manifestPath,(@{task=$plan.task;files=$moved.Count;bytes=($moved | Measure-Object -Property bytes -Sum).Sum;items=$moved} | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
}
Write-Output "ARCHIVED $($moved.Count) files with matching SHA-256 hashes."
