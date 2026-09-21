$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath 'D:\FPS3D\FPSGAME').Path
$archive = [IO.Path]::GetFullPath((Join-Path $project 'trash\witch-retired-20260921'))
$sourceRoot = Join-Path $project 'SourceAssets\WitchMeshy20260919'
$allowed = @($sourceRoot, (Join-Path $project 'Tools\Witch'), (Join-Path $project 'Tools\WitchFoundation'))
$targets = [Collections.Generic.List[string]]::new()
$dirs = @('Authoring\LocalRetarget','Delivery\LocalRetarget','Authoring\RobeGaitV03','Delivery\RobeGaitV03',
    'Delivery\LayeredV04','Authoring\LayeredV04\Fitted','Integration')
foreach ($rel in $dirs) {
    $dir = Join-Path $sourceRoot $rel
    if (Test-Path -LiteralPath $dir) {
        Get-ChildItem -LiteralPath $dir -File -Recurse | ForEach-Object { $targets.Add($_.FullName) }
    }
}
$files = @('local_retarget.py','local_retarget_manifest.json','robe_gait_v03.py','robe_gait_v03_manifest.json',
    'ROBE-GAIT-V03.md','ue_robe_gait_v03.json','Authoring\Witch_Idle_Candidate_v01.blend',
    'Delivery\A_Witch_Idle_Candidate_v01.fbx')
foreach ($rel in $files) { $targets.Add((Join-Path $sourceRoot $rel)) }
foreach ($role in @('Idle','Walk','CastPoison','ThrowPoisonBottle','DeathBackward')) {
    $targets.Add((Join-Path $sourceRoot "Authoring\LayeredV04\Witch_${role}_LayeredV04.blend"))
}
Get-ChildItem -LiteralPath (Join-Path $sourceRoot 'Authoring\OriginalRobeV05\Parts') -File |
    Where-Object { $_.Name -match '^Witch_(InnerBody|InnerCalves|Robe_SimProxy)' } |
    ForEach-Object { $targets.Add($_.FullName) }
$oldTools = @('import_witch.py','import_robe_gait_v03.py','import_layered_v04.py','activate_layered_v04.py',
    'activate_original_robe_v05.py','finish_witch.py','compile_clean_robe_v06.json','compile_layered_v04.json',
    'prepare_v04_build.py','close_for_v04_build.py','prepare_v05_build.py','close_for_v05_build.py',
    'prepare_spell_build.py','close_spell_support_editor.py','save_authorized_material_and_exit.py',
    'end_pie_for_v05_import.py','prepare_v05_cloth_repair.py','remove_v05_render_cage.py',
    'inspect_v05_source_geometry.py','inspect_v05_skirt_sections.py',
    'inspect_v05_skirt_after.py','diagnose_v05_lowerbody_source.py','read_visibility_editor_state.py',
    'read_v06_reimport_result.py','read_v06_import_scale.py','read_v06_idle_pose.py',
    'read_existing_witch_visibility.py','inspect_v06_invisible.py','inspect_v06_export_transform.py',
    'dump_v06_render_state.py')
foreach ($name in $oldTools) { $targets.Add((Join-Path $project "Tools\Witch\$name")) }
$targets.Add((Join-Path $project 'Tools\WitchFoundation\close_for_build.py'))
foreach ($root in @($sourceRoot,(Join-Path $project 'SourceAssets\WitchFoundation20260920'))) {
    Get-ChildItem -LiteralPath $root -File -Recurse | Where-Object { $_.Extension -match '^\.blend[0-9]+$' } |
        ForEach-Object { $targets.Add($_.FullName) }
}
$allowed += (Join-Path $project 'SourceAssets\WitchFoundation20260920')
$paths = @($targets | Sort-Object -Unique | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
# Validate every resolved source and destination before moving any file.
foreach ($path in $paths) {
    $full = (Resolve-Path -LiteralPath $path).Path
    if (-not (@($allowed | Where-Object { $full.StartsWith($_+'\',[StringComparison]::OrdinalIgnoreCase) }).Count)) {
        throw "Source outside witch scope: $full"
    }
    $rel = $full.Substring($project.Length+1)
    $dst = [IO.Path]::GetFullPath((Join-Path $archive $rel))
    if (-not $dst.StartsWith($archive+'\',[StringComparison]::OrdinalIgnoreCase)) { throw "Invalid archive path: $dst" }
    if (Test-Path -LiteralPath $dst) { throw "Archive already exists: $dst" }
}
$receipt = Join-Path $project 'Docs\AssetArchives\witch-retired-sources-20260921.json'
$rows = [Collections.Generic.List[object]]::new()
if (Test-Path -LiteralPath $receipt) { Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json | ForEach-Object {$rows.Add($_)} }
foreach ($path in $paths) {
    $full = (Resolve-Path -LiteralPath $path).Path
    $rel = $full.Substring($project.Length+1)
    $dst = [IO.Path]::GetFullPath((Join-Path $archive $rel))
    $size = (Get-Item -LiteralPath $full).Length
    $sha = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.Directory]::CreateDirectory((Split-Path -Parent $dst)) | Out-Null
    Move-Item -LiteralPath $full -Destination $dst
    if ((Get-Item -LiteralPath $dst).Length -ne $size -or (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha) {
        throw "Archived file differs: $dst"
    }
    $rows.Add([ordered]@{source=$rel.Replace('\','/');destination=$dst.Substring($project.Length+1).Replace('\','/');bytes=$size;sha256=$sha;
        reason='Superseded motion/robe output, rejected donor subpart, redundant backup or completed one-off repair';
        retained='Current V06/V07 problem comparison, intact WitchFoundation, preserved originals and required authoring inputs'})
    [IO.Directory]::CreateDirectory((Split-Path -Parent $receipt)) | Out-Null
    [IO.File]::WriteAllText($receipt, (ConvertTo-Json -InputObject @($rows.ToArray()) -Depth 5), [Text.UTF8Encoding]::new($false))
}
[pscustomobject]@{archived=$rows.Count;bytes=($rows | ForEach-Object { $_.bytes } | Measure-Object -Sum).Sum;manifest=$receipt} | ConvertTo-Json -Compress
