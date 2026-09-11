$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath('D:/FPS3D/FPSGAME')
$destination=Join-Path $root 'trash/optic-workflow-20260911'
if(Test-Path -LiteralPath $destination){throw 'Archive already exists; read its manifest before resuming.'}
$entries=@()
$lpvo='SourceAssets/LPVO1to6X20260911'
foreach($name in @('lpvo-first','lpvo-diagnose','lpvo-final','full-aperture-20260911','scope-release-20260911','__pycache__','LPVO_Editable.blend1','LPVO_SeparateParts.blend1','build_native.log','build_scope_view.log','build_scope_view_final.log','build_scope_view_release.log','build_scope_hud_final.log','build_scope_clean_hud.log','import.log','import_console.log')){
    $entries+=@{Path="$lpvo/$name";Reason='Superseded trial, backup, or failed build; final source and accepted comparison retained';Replacement="$lpvo/scope-clean-hud-20260911; $lpvo/LPVO_Editable.blend"}
}
$entries+=@{Path='SourceAssets/PanoramicRedDot20260911/Reroll02';Reason='Rejected distorted reference trials superseded by Reroll03';Replacement='SourceAssets/PanoramicRedDot20260911/Reroll03; SourceAssets/PanoramicRedDot20260911/GameIntegration'}
$entries+=@{Path='SourceAssets/PrismScope2X20260911/OpticalRefinement';Reason='Superseded by regular machined controls; final script reads parent master directly';Replacement='SourceAssets/PrismScope2X20260911/MachinedControls'}
$entries+=@{Path='SourceAssets/PrismScope2X20260911/scope2x-first';Reason='Initial audit superseded by final machined optic';Replacement='SourceAssets/PrismScope2X20260911/MachinedControls'}
foreach($relative in @('SourceAssets/PrismScope2X20260911/__pycache__','SourceAssets/PanoramicRedDot20260911/__pycache__')){$entries+=@{Path=$relative;Reason='Python bytecode cache';Replacement='Retained Python source'}}
$manifest=@()
foreach($entry in $entries){
    $source=[IO.Path]::GetFullPath((Join-Path $root $entry.Path))
    $target=[IO.Path]::GetFullPath((Join-Path $destination $entry.Path))
    if(!$source.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase) -or !$target.StartsWith($destination+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Path escaped archive scope'}
    if(!(Test-Path -LiteralPath $source)){continue}
    $files=if((Get-Item -LiteralPath $source).PSIsContainer){@(Get-ChildItem -LiteralPath $source -File -Recurse)}else{@(Get-Item -LiteralPath $source)}
    foreach($file in $files){
        $relative=$file.FullName.Substring($root.Length+1).Replace('\','/')
        $manifest+=@{original=$relative;destination=('trash/optic-workflow-20260911/'+$relative);bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash;reason=$entry.Reason;replacement=$entry.Replacement}
    }
}
New-Item -ItemType Directory -Path $destination | Out-Null
$manifest|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $destination 'manifest.json') -Encoding utf8
foreach($item in $manifest){
    $source=Join-Path $root $item.original;$target=Join-Path $root $item.destination
    if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne $item.sha256){throw "Source changed: $source"}
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Move-Item -LiteralPath $source -Destination $target
    if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $item.sha256){throw "Archive hash mismatch: $target"}
}
# Only empty directories in the explicitly selected source paths are removed.
foreach($entry in $entries){$source=Join-Path $root $entry.Path;if(Test-Path -LiteralPath $source -PathType Container){
    Get-ChildItem -LiteralPath $source -Directory -Recurse|Sort-Object {$_.FullName.Length} -Descending|ForEach-Object {if(!(Get-ChildItem -LiteralPath $_.FullName -Force)){Remove-Item -LiteralPath $_.FullName}}
    if(!(Get-ChildItem -LiteralPath $source -Force)){Remove-Item -LiteralPath $source}
}}
$docs=Join-Path $root 'Docs/Weapons';New-Item -ItemType Directory -Path $docs -Force|Out-Null
Copy-Item -LiteralPath (Join-Path $destination 'manifest.json') -Destination (Join-Path $docs 'optic-archive-20260911.json')
Write-Output ("Archived {0} files, {1:N0} bytes; all hashes verified" -f $manifest.Count,($manifest|Measure-Object bytes -Sum).Sum)
