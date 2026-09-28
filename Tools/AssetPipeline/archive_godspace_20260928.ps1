# Scoped retirement of replaced God Space authoring files; never moves live UE packages.
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$sourceRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot 'SourceAssets/GodSpaceLayout20260927'))
$archiveRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot 'trash/godspace-publication-20260928'))
if(-not $sourceRoot.StartsWith($projectRoot+'\',[StringComparison]::OrdinalIgnoreCase) -or
   -not $archiveRoot.StartsWith($projectRoot+'\trash\',[StringComparison]::OrdinalIgnoreCase)){throw 'Archive scope mismatch'}
$groups=@(
    @{reason='Distant earth replaced by the continuous ocean';replacement='Integration/author_distant_ocean.py';paths=@(
        'Integration/author_distant_earth.py','Integration/import_distant_earth.py','Integration/resume_earth_custom_inputs.py',
        'Integration/export_library_ground.py','Integration/read_earth_context.py','Integration/read_earth_colour_boundary.py',
        'Integration/EarthLibrary','Integration/EarthRepair','Integration/Exported/SM_GodSpaceDistantEarth.fbx',
        'Integration/Exported/T_GodSpaceEarth_BaseColor.png','Integration/Exported/T_GodSpaceEarth_Normal.png')},
    @{reason='Superseded cloud field and rejected fixed lighting compensation';replacement='Integration/build_cloud_sea.py (retained but hidden)';paths=@(
        'Integration/CloudSeaCoverage.hlsl','Integration/CloudSeaDensity.hlsl','Integration/CloudSeaAmbientFill.hlsl',
        'Integration/CloudSeaLightBalance.hlsl','Integration/cloud_sea_lighting.py','Integration/produce_cloud_lighting.py',
        'Integration/fix_cloud_sea_position.py','Integration/increase_cloud_sea.py','Integration/Receipts/resume-cloud-double.py')},
    @{reason='Unselected local textile candidate; approved Carpet 01 remains';replacement='Integration/CarpetSources/T_Carpet_01_N.tga';paths=@(
        'Integration/CarpetSources/T_Carpet_02_BC.png','Integration/CarpetSources/T_Carpet_02_BC.tga',
        'Integration/CarpetSources/T_Carpet_02_N.png','Integration/CarpetSources/T_Carpet_02_N.tga','Integration/CarpetSources/T_Carpet_02_R.tga')},
    @{reason='Superseded regular-wave source and unused exported normal candidates';replacement='Integration/build_reused_ocean_spectrum.py';paths=@(
        'Integration/OceanChop.hlsl','Integration/OceanWaveSources/T_Ocean_Waves01_Normals.png',
        'Integration/OceanWaveSources/T_Ocean_Waves02_Normals.png','Integration/OceanWaveSources/T_Water_Normal.png')},
    @{reason='Old structure export replaced by connected trim; original rebuild inputs retained';replacement='Integration/FloorTrim/SM_GodSpaceStructure_TrimV2.fbx';paths=@(
        'Integration/Exported/SM_GodSpaceStructure.fbx','Integration/FloorTrim/placements-before.json')},
    @{reason='Automatic backup superseded by retained editable source';replacement='Same path without final 1';paths=@(
        'GodSpace_Layout_V1.blend1','Integration/FloorTrim/Structure_TrimV2.blend1')},
    @{reason='Completed one-off source patcher and pre-edit source copies; actual source is published';replacement='Source/FPSGAME and current authoring scripts';paths=@(
        'Integration/BeforeSource','Integration/update_runtime_routes.py','finalize_manifest.py','update_delivery_notes.py')}
)
$manifestPath=Join-Path $projectRoot 'Docs/AssetArchives/godspace-20260928.json'
if(Test-Path -LiteralPath $manifestPath){throw 'Archive manifest already exists; preserve it and resume from its exact records'}
$records=@()
foreach($group in $groups){foreach($relative in $group.paths){
    $candidate=[IO.Path]::GetFullPath((Join-Path $sourceRoot $relative))
    if(-not $candidate.StartsWith($sourceRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid source path'}
    if(-not (Test-Path -LiteralPath $candidate)){throw "Missing planned source: $relative"}
    $item=Get-Item -LiteralPath $candidate
    $files=if($item.PSIsContainer){Get-ChildItem -LiteralPath $candidate -File -Recurse}else{@($item)}
    foreach($file in $files){
        $sourceRelative=$file.FullName.Substring($projectRoot.Length+1).Replace('\','/')
        $destination=[IO.Path]::GetFullPath((Join-Path $archiveRoot $sourceRelative))
        if(-not $destination.StartsWith($archiveRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid destination'}
        if(Test-Path -LiteralPath $destination){throw "Destination exists: $destination"}
        $records+=@{original=$sourceRelative;destination=$destination.Substring($projectRoot.Length+1).Replace('\','/');bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant();reason=$group.reason;replacement=$group.replacement}
    }
}}
[IO.Directory]::CreateDirectory($archiveRoot)|Out-Null
# Persist the plan before mutation so an interrupted move can be recovered.
$encoding=[Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText((Join-Path $archiveRoot 'move-plan.json'),(ConvertTo-Json -Depth 6 -InputObject $records)+"`n",$encoding)
foreach($record in $records){
    $src=Join-Path $projectRoot $record.original
    $dst=Join-Path $projectRoot $record.destination
    if((Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant() -ne $record.sha256){throw 'Source changed during archival'}
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($dst))|Out-Null
    Move-Item -LiteralPath $src -Destination $dst
    if((Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant() -ne $record.sha256){throw 'Moved file hash mismatch'}
}
$report=@{date='2026-09-28';scope='God Space authoring retirement';files=$records;file_count=$records.Count;bytes=($records|Measure-Object -Property bytes -Sum).Sum;ue_packages_moved=$false;runtime_tested=$false}
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($manifestPath))|Out-Null
[IO.File]::WriteAllText($manifestPath,(ConvertTo-Json -Depth 8 -InputObject $report)+"`n",$encoding)
[IO.File]::WriteAllText((Join-Path $archiveRoot 'README.md'),"# God Space retired authoring files`n`nExact original paths, SHA-256, reasons and replacements are in move-plan.json and Docs/AssetArchives/godspace-20260928.json. No live UE package was moved. Retained originals used by the current build are not waste. Restore a named file only when intentionally recovering historical work.`n",$encoding)
Write-Output ("Archived {0} files, {1:N0} bytes; hashes matched." -f $report.file_count,$report.bytes)
