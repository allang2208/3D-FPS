param([Parameter(Mandatory=$true)][string]$Batch,[ValidateSet("R1","R2","R3","R4","WorkwearR5","WorkwearR6")][string]$Revision="R1")
$ErrorActionPreference='Stop'
$project=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$source=Join-Path $project 'SourceAssets/HillsVillageHighWall20261120/MasterArtisan'
$env:MASTER_ARTISAN_HEAD_REVISION=$Revision
$recipe='save_assets.py'
$stage=Join-Path $Batch 'Host'
$characters=Join-Path $stage 'Content/Characters'
New-Item -ItemType Directory -Path $characters -Force | Out-Null
Copy-Item -LiteralPath "$project/SourceAssets/VillageBlacksmithNPC20261118/HeadHair/AuthoringHost/SmithHead.uproject" -Destination "$stage/Artisan.uproject" -Force
foreach($rel in @('AsianMale_Jason','Characters/VillageBlacksmithNPC20261118','Characters/ModularOutfit20260924')) {
    $link=Join-Path "$stage/Content" $rel
    if (!(Test-Path -LiteralPath $link)) {New-Item -ItemType Junction -Path $link -Target (Join-Path "$project/Content" $rel) | Out-Null}
}
if($Revision -in @('R3','WorkwearR5','WorkwearR6')){
    $owner='Characters/VillageMasterArtisan'
    New-Item -ItemType Directory -Path "$stage/Content/$owner" -Force | Out-Null
    foreach($rel in @('Materials','Textures')){
        $link="$stage/Content/$owner/$rel"
        if(!(Test-Path -LiteralPath $link)){New-Item -ItemType Junction -Path $link -Target "$project/Content/$owner/$rel" | Out-Null}
    }
    if($Revision -eq 'WorkwearR6' -and !(Test-Path -LiteralPath "$stage/Content/$owner/WorkwearR5")){
        New-Item -ItemType Junction -Path "$stage/Content/$owner/WorkwearR5" -Target "$project/Content/$owner/WorkwearR5" | Out-Null
    }
}
$env:UE_SKIP_UBT_SDK_SETUP='1'
$cmd='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
& $cmd "$stage/Artisan.uproject" -run=pythonscript "-script=$PSScriptRoot/$recipe" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' '-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache' '-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen' '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT' "-abslog=$Batch/author.log" *> "$Batch/console.log"
if($LASTEXITCODE -ne 0){throw "Asset authoring failed. See $Batch/author.log"}
if($Revision -ne 'R1'){return}
$saved=Get-Content "$source/saved.json" -Raw | ConvertFrom-Json
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
try {
    try { $null=$mutex.WaitOne() } catch [Threading.AbandonedMutexException] {}
    $folder='Content/Characters/VillageMasterArtisan'
    $files=foreach($pkg in $saved.packages) {
        if(!$pkg.StartsWith('/Game/Characters/VillageMasterArtisan/')){throw "Unexpected asset $pkg"}
        $rel='Content/'+$pkg.Substring(6)+'.uasset'
        $src=Join-Path $stage $rel
        $dst=Join-Path $project $rel
        if((Test-Path -LiteralPath $dst) -and (Get-FileHash -LiteralPath $src).Hash -ne (Get-FileHash -LiteralPath $dst).Hash){throw "Destination independently occupied: $dst"}
        [pscustomobject]@{source=$src; target=$dst; package=$pkg}
    }
    foreach($file in $files){
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $file.target) | Out-Null
        if(!(Test-Path -LiteralPath $file.target)){Copy-Item -LiteralPath $file.source -Destination $file.target}
    }
    $saved | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$Batch/published.json" -Encoding utf8
    Write-Output "Saved $($files.Count) packages to $folder"
} finally {$mutex.ReleaseMutex();$mutex.Dispose()}
