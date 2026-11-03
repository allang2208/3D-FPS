param([string]$ProjectRoot = 'D:/FPS3D/FPSGAME')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $ProjectRoot).Path.TrimEnd('\', '/')
$archive = Join-Path $root 'trash/m24-bipod-20261103'
$publication = Join-Path $root 'Docs/Publication/M24Bipod20261103'
$network = 'Saved/M24BipodNetworkReview20261103'
$parity = 'Saved/M24BipodParity20261103'
$retired = @(
    "$network/editor_state.py", "$network/editor-app-schema.json", "$network/editor-app-schema2.json",
    "$network/editor-state.txt", "$network/livecoding-schema.txt", "$network/toolsets.json",
    "$network/native_check-backup-2026.11.03-09.43.52.log",
    "$network/startup-sdk-wait-console.log", "$network/startup-sdk-wait.log", "$parity/toolsets.json",
    "$network/Before/M24BipodValidation.inl", "$network/Before/WeaponBipodDeploymentComponent.cpp",
    "$network/Before/WeaponBipodDeploymentComponent.h", "$parity/Before/FPSBodyKukriMotion.h",
    "$parity/Before/M24BipodValidation.inl", "$parity/Before/WeaponBipodDeploymentComponent.cpp",
    "$parity/Before/WeaponBipodDeploymentComponent.h"
)
function Assert-LocalPath([string]$Path) {
    $absolute = [IO.Path]::GetFullPath($Path)
    if (!$absolute.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Outside project: $absolute" }
    $parent = $absolute
    while ($parent -and $parent -ne $root) {
        if (Test-Path -LiteralPath $parent) {
            $item = Get-Item -LiteralPath $parent -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point: $parent" }
        }
        $parent = Split-Path -Parent $parent
    }
}
$plan = foreach ($relative in $retired) {
    $source = Join-Path $root $relative
    $target = Join-Path $archive $relative
    Assert-LocalPath $source
    Assert-LocalPath $target
    if (Test-Path -LiteralPath $target) { throw "Archive already exists: $target" }
    $item = Get-Item -LiteralPath $source
    if ($item.PSIsContainer) { throw "Expected a file: $source" }
    [pscustomobject][ordered]@{
        source=$relative; target=('trash/m24-bipod-20261103/' + $relative)
        bytes=$item.Length; sha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        reason= $(if ($relative -like '*/Before/*') {'Superseded pre-fix source snapshot; recoverable archive'} else {'Abandoned editor probe or SDK-blocked startup artifact'})
        retained='Current Source/FPSGAME files; successful native_cases.json, native_check.py, logs and delivery receipts in both Saved review directories'
    }
}
Assert-LocalPath $publication
New-Item -ItemType Directory -Path $publication -Force | Out-Null
$plan | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $publication 'archive-manifest.json') -Encoding utf8
foreach ($entry in $plan) {
    $source = Join-Path $root $entry.source
    $target = Join-Path $root $entry.target
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $entry.sha256) { throw "Source changed: $source" }
    Move-Item -LiteralPath $source -Destination $target
    if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $entry.sha256 -or (Test-Path -LiteralPath $source)) { throw "Archive readback failed: $target" }
}
[ordered]@{ files=$plan.Count; bytes=($plan | Measure-Object bytes -Sum).Sum; hashes_verified=$true; permanently_deleted=$false } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $publication 'archive-receipt.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $publication 'archive-receipt.json')
