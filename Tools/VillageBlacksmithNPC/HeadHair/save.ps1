param([switch]$MaterialsOnly)
$ErrorActionPreference = 'Stop'
$project = 'D:/FPS3D/FPSGAME'
$data = "$project/SourceAssets/VillageBlacksmithNPC20261118/HeadHair"
$hostRoot = "$data/AuthoringHost"
if ($env:SMITH_NAPE_REVISION -eq '1') { $hostRoot = "$data/NeckFinishHost" }
New-Item -ItemType Directory -Force -Path "$hostRoot/Content/Characters/ModularOutfit20260924","$hostRoot/Content/Characters/VillageBlacksmithNPC20261118" | Out-Null
$mounts = @{
    "$hostRoot/Content/AsianMale_Jason" = "$project/Content/AsianMale_Jason"
    "$hostRoot/Content/Characters/ModularOutfit20260924/JasonStrong20261117" = "$project/SourceAssets/JasonStrong20261117/AuthoringHost/Content/Characters/ModularOutfit20260924/JasonStrong20261117"
    "$hostRoot/Content/Characters/ModularOutfit20260924/ArmoredBoots20261004" = "$project/Content/Characters/ModularOutfit20260924/ArmoredBoots20261004"
    "$hostRoot/Content/Characters/ModularOutfit20260924/JasonPlayer20261003" = "$project/Content/Characters/ModularOutfit20260924/JasonPlayer20261003"
}
foreach($mount in $mounts.GetEnumerator()) {
    if(-not (Test-Path -LiteralPath $mount.Key)){ New-Item -ItemType Junction -Path $mount.Key -Target $mount.Value | Out-Null }
}
$pluginList = Get-Content -Raw "$project/SourceAssets/JasonStrong20261117/AuthoringHost/JasonAuthoring.uproject" | ConvertFrom-Json
$manifest = [ordered]@{ FileVersion=3; EngineAssociation='5.8'; Plugins=$pluginList.Plugins }
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$hostRoot/SmithHead.uproject" -Encoding utf8
$env:UE_SKIP_UBT_SDK_SETUP = '1'
if($MaterialsOnly){$env:SMITH_HAIR_MATERIALS_ONLY='1'} else {Remove-Item Env:SMITH_HAIR_MATERIALS_ONLY -ErrorAction SilentlyContinue}
$cmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
& $cmd "$hostRoot/SmithHead.uproject" -run=pythonscript "-script=$PSScriptRoot/save_meshes.py" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$data/save.log" *> "$data/save.console.log"
if($LASTEXITCODE -ne 0){throw "Head authoring commandlet returned $LASTEXITCODE"}
if($MaterialsOnly){return}
if ($env:SMITH_NAPE_REVISION -eq '1') {
    $receipt=Get-Content -Raw "$data/saved.json" | ConvertFrom-Json
    $changed=@('SK_Smith_Head','HeadParts/M_Smith_NativeNeck')
    $npc='Content/Characters/VillageBlacksmithNPC20261118'
    $mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
    $held=$false
    try {
        try { $held=$mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held=$true }
        foreach($part in $changed) {
            $file="$npc/$part.uasset"
            $live=(Get-FileHash -LiteralPath "$project/$file").Hash
            if($live -ne (Get-FileHash -LiteralPath "$data/AuthoringHost/$file").Hash -and $live -ne (Get-FileHash -LiteralPath "$hostRoot/$file").Hash){throw "The installed $part was edited separately."}
        }
        foreach($part in $changed) {
            $file="$npc/$part.uasset"
            $temporary="$project/$file.nape.tmp"
            [IO.File]::Copy("$hostRoot/$file",$temporary,$true)
            [IO.File]::Move($temporary,"$project/$file",$true)
        }
        $receipt | Add-Member NoteProperty neck_revision 'Raised the nape cut above the generated collar'
        $receipt | ConvertTo-Json -Depth 6 | Set-Content "$data/installed.json" -Encoding utf8
    } finally { if($held){$mutex.ReleaseMutex()};$mutex.Dispose() }
    return
}
& "$PSScriptRoot/install_new_packages.ps1"
