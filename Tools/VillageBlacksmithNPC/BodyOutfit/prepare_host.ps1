$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$working="$projectRoot/SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit"
$hostRoot="$working/Host"
$targetContent="$hostRoot/Content"
foreach ($dir in @("$working/Inputs", "$working/Textures", "$targetContent/Characters/ModularOutfit20260924")) {New-Item -ItemType Directory -Force -Path $dir | Out-Null}
$originalHost="$projectRoot/SourceAssets/JasonStrong20261117/AuthoringHost"
$plugins=Get-Content "$originalHost/JasonAuthoring.uproject" -Raw | ConvertFrom-Json
$plugins.PSObject.Properties.Remove('Modules')
$plugins | ConvertTo-Json -Depth 8 | Set-Content -Encoding ascii "$hostRoot/SmithBody.uproject"
function MountFolders($source,$dest,$skip) {
    foreach ($item in (Get-ChildItem -Directory -LiteralPath $source)) {
        if ($skip -contains $item.Name) {continue}
        $target=Join-Path $dest $item.Name
        if (!(Test-Path -LiteralPath $target)) {New-Item -ItemType Junction -Path $target -Target $item.FullName | Out-Null}
    }
}
MountFolders "$projectRoot/Content" $targetContent @('Characters','Developers','Collections','__ExternalActors__','__ExternalObjects__','Maps','WorldGeneration')
MountFolders "$projectRoot/Content/Characters" "$targetContent/Characters" @('ModularOutfit20260924','VillageBlacksmithNPC20261118')
MountFolders "$projectRoot/Content/Characters/ModularOutfit20260924" "$targetContent/Characters/ModularOutfit20260924" @('JasonStrong20261117')
$local='Characters/ModularOutfit20260924/JasonStrong20261117'
if (!(Test-Path "$targetContent/$local")) {New-Item -ItemType Junction -Path "$targetContent/$local" -Target "$originalHost/Content/$local" | Out-Null}
