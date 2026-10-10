param([switch]$Apply)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME')
$sourceRoot=Join-Path $project 'SourceAssets/BoundCongregateMeshy20261006'
$toolRoot=Join-Path $project 'Tools/BoundCongregate'
$archive=Join-Path $project 'trash/bound-congregate-publication-20261010'
$manifestPath=Join-Path $project 'Docs/Monsters/bound-congregate-retirement-20261010.json'
$entries=@{}
function Add-ArchiveFile($file,$reason,$replacement) {
    $path=[IO.Path]::GetFullPath($file.FullName)
    if(!$path.StartsWith($sourceRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -and
       !$path.StartsWith($toolRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {
        throw "Outside the M-88 archive scope: $path"
    }
    if($file.Attributes -band [IO.FileAttributes]::ReparsePoint){throw "Unexpected linked file: $path"}
    if(!$entries.ContainsKey($path)) {
        $relative=[IO.Path]::GetRelativePath($project,$path).Replace('\','/')
        $destination=[IO.Path]::GetFullPath((Join-Path $archive $relative))
        if(!$destination.StartsWith($archive+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) {throw 'Archive path escaped'}
        if(Test-Path -LiteralPath $destination){throw "Archive target already exists: $destination"}
        $entries[$path]=[pscustomobject][ordered]@{source=$relative;destination=[IO.Path]::GetRelativePath($project,$destination).Replace('\','/');bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant();reason=$reason;replacement=$replacement}
    }
}
foreach($name in @('GarmentDrapeV20','GarmentDrapeV21','GarmentDrapeV23')) {
    Get-ChildItem -LiteralPath (Join-Path $sourceRoot $name) -File -Recurse | ForEach-Object {
        Add-ArchiveFile $_ 'Rejected floating/intersecting garment candidate; no current source reads this output.' 'GarmentDrapeV24 reference, GarmentDrapeV25 source, TentacleReachV29 live mesh'
    }
}
foreach($name in @('FlurryV22','FlurryV26','FlurryV27')) {
    Get-ChildItem -LiteralPath (Join-Path $sourceRoot $name) -File -Recurse | ForEach-Object {
        Add-ArchiveFile $_ 'Superseded attack authoring output and its historical review; V28 reads V25 directly.' 'CombatV28 accepted flurry and bite source'
    }
}
Get-ChildItem -LiteralPath $toolRoot -File | Where-Object {
    $_.Name -match '(garment_v(20|21|23)|flurry_v(22|26|27))' -or
    $_.Name -in @('revise_garment_v21_source.py','rebind_garment_v23_contact.py')
} | ForEach-Object {
    Add-ArchiveFile $_ 'Retired candidate author/import/review entry; recover explicitly before replaying history.' 'author_garment_v25.py, author_combat_v28.py and current import tools'
}
Get-ChildItem -LiteralPath $toolRoot -File | Where-Object {
    $_.Name -match '^(close_for_(bite_v33|capture_v30)_build|compile_(combat_v28|death_v32|garment_v24|garment_v25)_editor|end_play_for_(combat_v28|garment_v24|garment_v25)|stop_pie_(bite_v33|death_v32)|finish_death_v34_editor)\.py$'
} | ForEach-Object {
    Add-ArchiveFile $_ 'Completed one-off editor stop/compile/retry helper.' 'Normal background build/install scripts; existing editor bridge only when needed'
}
Get-ChildItem -LiteralPath $sourceRoot -File -Recurse | Where-Object {
    $_.Extension -eq '.blend1' -or $_.FullName -match '[\\/]before[\\/]' -or
    $_.Name -match '(^stop-pie.*\.txt$|bridge.*\.txt$|-backup-.*\.log$|^garment-v20-author.*\.log$)'
} | ForEach-Object {
    Add-ArchiveFile $_ 'Superseded snapshot or completed transport/retry record; retained here for recovery.' 'Current authored source, delivery.json and final build/save logs at original paths'
}
$cache=Join-Path $toolRoot '__pycache__'
if(Test-Path -LiteralPath $cache) {
    Get-ChildItem -LiteralPath $cache -File -Recurse | ForEach-Object {Add-ArchiveFile $_ 'Generated Python bytecode for finished production.' 'Retained Python source'}
}
$files=@($entries.Values | Sort-Object source)
$report=[ordered]@{date='2026-10-10';scope='BoundCongregate V20-V34 publication';archive='trash/bound-congregate-publication-20261010';count=$files.Count;bytes=($files | Measure-Object -Property bytes -Sum).Sum;complete=$false;files=$files}
if(!$Apply) {
    $plan=Join-Path $project 'Saved/BoundCongregatePublication20261010/archive-plan.json'
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $plan -Encoding utf8
    Write-Output "Archive plan: $($report.count) files, $($report.bytes) bytes. $plan"
    return
}
if(Test-Path -LiteralPath $manifestPath){throw 'Do not overwrite an existing archive manifest'}
New-Item -ItemType Directory -Force -Path $archive | Out-Null
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
foreach($item in $files) {
    $from=Join-Path $project $item.source
    $to=Join-Path $project $item.destination
    if((Get-FileHash -LiteralPath $from -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256){throw "Source changed: $from"}
    New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($to)) | Out-Null
    Move-Item -LiteralPath $from -Destination $to
    if((Get-Item -LiteralPath $to).Length -ne $item.bytes -or (Get-FileHash -LiteralPath $to -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256){throw "Archive readback mismatch: $to"}
}
$report.complete=$true
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Copy-Item -LiteralPath $manifestPath -Destination (Join-Path $archive 'manifest.json')
@'
# M-88 retired production files

This local archive retains rejected/superseded candidates and completed process files.
See manifest.json for original paths, sizes, SHA-256, reasons and retained replacements.
Content packages, current V25/V28/V29 sources, V32 corpse inputs and V34 profile remain in place.
To recover an entry, compare its SHA-256 then copy it to its original path only if that path is free.
Restoring a rejected authoring script does not authorize running it over current assets.
'@ | Set-Content -LiteralPath (Join-Path $archive 'README.md') -Encoding utf8
Write-Output "Archived and read back $($report.count) files, $($report.bytes) bytes."
