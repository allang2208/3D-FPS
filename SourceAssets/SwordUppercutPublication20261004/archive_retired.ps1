$ErrorActionPreference = 'Stop'
$uppercutRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..')).TrimEnd('\')
$uppercutTrash = [IO.Path]::GetFullPath((Join-Path $uppercutRoot 'trash/sword-uppercut-retired-20261004')).TrimEnd('\')
$uppercutPlan = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'archive-plan.json') -Raw | ConvertFrom-Json
$uppercutAllowed = @('SourceAssets/SwordUppercut20261003/','SourceAssets/SwordUppercut20261004/','SourceAssets/SkillIconRoundedSquare20261004/')
$uppercutManifest = @()

foreach ($entry in $uppercutPlan) {
    $source = [IO.Path]::GetFullPath((Join-Path $uppercutRoot $entry.source))
    $destination = [IO.Path]::GetFullPath((Join-Path $uppercutRoot $entry.destination))
    $inScope = $entry.source -eq 'Source/FPSGAME/Weapons/RuneSwordUppercutRhythm.h'
    foreach ($prefix in $uppercutAllowed) { if ($entry.source.StartsWith($prefix)) { $inScope = $true } }
    if (!$inScope -or !$source.StartsWith($uppercutRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or
        !$destination.StartsWith($uppercutTrash+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Archive path outside task scope' }
    $item = Get-Item -LiteralPath $source -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Archive source is a reparse point: $source" }
    if (Test-Path -LiteralPath $destination) { throw "Archive destination already exists: $destination" }
    $files = if ($item.PSIsContainer) { @(Get-ChildItem -LiteralPath $source -Recurse -File -Force) } else { @($item) }
    foreach ($file in $files) {
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Archive file is a reparse point: $($file.FullName)" }
        $relative = $file.FullName.Substring($uppercutRoot.Length+1).Replace('\','/')
        $uppercutManifest += [pscustomobject]@{
            original=$relative; destination=('trash/sword-uppercut-retired-20261004/'+$relative)
            bytes=$file.Length; sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            reason=$entry.reason; retained=$entry.retained
        }
    }
}
$uppercutManifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'archive-manifest.json') -Encoding UTF8
foreach ($entry in $uppercutPlan) {
    $source = [IO.Path]::GetFullPath((Join-Path $uppercutRoot $entry.source))
    $destination = [IO.Path]::GetFullPath((Join-Path $uppercutRoot $entry.destination))
    if (!$source.StartsWith($uppercutRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or
        !$destination.StartsWith($uppercutTrash+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Resolved archive path escaped workspace' }
    [IO.Directory]::CreateDirectory((Split-Path -Parent $destination)) | Out-Null
    Move-Item -LiteralPath $source -Destination $destination
}
foreach ($entry in $uppercutManifest) {
    $file = Get-Item -LiteralPath (Join-Path $uppercutRoot $entry.destination)
    if ($file.Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) {
        throw "Archive readback mismatch: $($entry.destination)"
    }
}
$uppercutCount = $uppercutManifest.Count
$uppercutBytes = ($uppercutManifest | Measure-Object -Property bytes -Sum).Sum
Write-Output "Archived $uppercutCount files, $uppercutBytes bytes; SHA-256 readback matched."
