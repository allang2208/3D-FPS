$ErrorActionPreference='Stop'
$source='D:/FPS3D/ThunderHammerFullReviewHost20261102'
$target='D:/FPS3D/ThunderHammerHeadlessBodyHost20261103'
if(Test-Path -LiteralPath $target){throw 'Isolated headless host already exists; preserve it rather than overwrite.'}
New-Item -ItemType Directory -Path $target | Out-Null
Copy-Item -LiteralPath "$source/FPSGAME.uproject" -Destination "$target/FPSGAME.uproject"
Copy-Item -LiteralPath "$source/Config" -Destination "$target/Config" -Recurse
foreach($name in @('Binaries','Plugins')){
    New-Item -ItemType Junction -Path "$target/$name" -Target "$source/$name" | Out-Null
}
New-Item -ItemType Directory -Path "$target/Content" | Out-Null
foreach($entry in Get-ChildItem -LiteralPath "$source/Content" -Force){
    $dest=Join-Path "$target/Content" $entry.Name
    if($entry.Name -eq 'ColdSteelData'){
        New-Item -ItemType Directory -Path $dest | Out-Null
        foreach($data in Get-ChildItem -LiteralPath $entry.FullName -Force){
            $dataDest=Join-Path $dest $data.Name
            if($data.PSIsContainer){New-Item -ItemType Junction -Path $dataDest -Target $data.FullName | Out-Null}
            else{Copy-Item -LiteralPath $data.FullName -Destination $dataDest}
        }
    }elseif($entry.PSIsContainer){New-Item -ItemType Junction -Path $dest -Target $entry.FullName | Out-Null}
    else{Copy-Item -LiteralPath $entry.FullName -Destination $dest}
}
$bodyPath="$target/Content/ColdSteelData/player_body.json"
$body=Get-Content -LiteralPath $bodyPath -Raw | ConvertFrom-Json
$original=$body.body_mesh
# Keep the real body, hammer and generic locomotion assets. Other weapons and
# furniture clips are irrelevant to this unrendered hammer-only host.
$allClips=@($body.clips.psobject.Properties)
foreach($clip in $allClips){
    if($clip.Name -notmatch '^(Warhammer|Unarmed|Melee|Crouch)\.' -and $clip.Name.Contains('.')){
        $body.clips.psobject.Properties.Remove($clip.Name)
    }
}
$body | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $bodyPath -Encoding utf8
@{source=$source;target=$target;body_mesh=$original;clips_before=$allClips.Count;clips_retained=@($body.clips.psobject.Properties).Count;scope='Unrendered host retains original body and hammer/generic locomotion clips; other weapon/furniture clips omitted. Real input and state replication remain active. Observer uses untouched full content. No production content modified.'} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/headless-host-scope.json" -Encoding utf8
Write-Output "THUNDER_HEADLESS_HOST_READY $target"
