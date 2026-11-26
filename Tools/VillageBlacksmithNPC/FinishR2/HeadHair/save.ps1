$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$base="$project/SourceAssets/VillageBlacksmithNPC20261118"
$work="$base/FinishR2/HeadHair"
$oldHost="$base/HeadHair/NeckFinishHost"
$stage="$work/Host"
$folder='Content/Characters/VillageBlacksmithNPC20261118'
New-Item -ItemType Directory -Force -Path "$stage/$folder","$stage/Content/Characters/ModularOutfit20260924" | Out-Null
Get-ChildItem -LiteralPath "$oldHost/Content/Characters/ModularOutfit20260924" -Directory | ForEach-Object {
    $mount=Join-Path "$stage/Content/Characters/ModularOutfit20260924" $_.Name
    if(-not (Test-Path -LiteralPath $mount)){New-Item -ItemType Junction -Path $mount -Target $_.FullName | Out-Null}
}
foreach($rel in @('Content/AsianMale_Jason',"$folder/HeadParts")){
    $mount="$stage/$rel"
    if(-not (Test-Path -LiteralPath $mount)){New-Item -ItemType Junction -Path $mount -Target "$project/$rel" | Out-Null}
}
Copy-Item -LiteralPath "$oldHost/SmithHead.uproject" -Destination "$stage/SmithHead.uproject" -Force
$env:UE_SKIP_UBT_SDK_SETUP='1'
$ep='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
& $ep "$stage/SmithHead.uproject" -run=pythonscript "-script=$PSScriptRoot/save_head.py" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$work/save.log" *> "$work/save.console.log"
if($LASTEXITCODE -ne 0){throw "UE head publication failed ($LASTEXITCODE)"}
$receipt=Get-Content -Raw "$work/saved.json" | ConvertFrom-Json
$lock=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    try{$held=$lock.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    $files=@()
    foreach($package in $receipt.packages){
        if($package -notlike '/Game/Characters/VillageBlacksmithNPC20261118/HeadFinishR2/*' -and $package -ne '/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Head'){throw "Unexpected package $package"}
        $rel='Content/'+$package.Substring(6)+'.uasset'
        $src="$stage/$rel";$dst="$project/$rel"
        $hash=(Get-FileHash -LiteralPath $src).Hash
        if(Test-Path -LiteralPath $dst){
            $actual=(Get-FileHash -LiteralPath $dst).Hash
            if($actual -ne $hash){
                if($package -ne '/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Head' -or $actual -ne (Get-FileHash -LiteralPath "$oldHost/$rel").Hash){throw "Concurrent modification to $package"}
            }
        }
        $files+=@([pscustomobject]@{source=$src;destination=$dst;sha256=$hash;package=$package})
    }
    # Publish versioned dependencies first; replace the consumer only after all are available.
    foreach($f in ($files|Sort-Object {$_.package.EndsWith('/SK_Smith_Head')})){
        $dst=$f.destination
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst)|Out-Null
        if((Test-Path -LiteralPath $dst) -and (Get-FileHash -LiteralPath $dst).Hash -eq $f.sha256){continue}
        $partial="$dst.smithheadr2.tmp"
        [IO.File]::Copy($f.source,$partial,$true)
        [IO.File]::Move($partial,$dst,$true)
    }
    [ordered]@{head=$receipt.head;skeleton=$receipt.skeleton;lods=$receipt.lods;files=$files;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 5 | Set-Content "$work/installed.json" -Encoding utf8
}finally{if($held){$lock.ReleaseMutex()};$lock.Dispose()}

