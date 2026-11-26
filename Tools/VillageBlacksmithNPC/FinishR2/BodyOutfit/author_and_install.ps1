$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$base="$project/SourceAssets/VillageBlacksmithNPC20261118"
$out="$base/FinishR2/BodyOutfit"
$hostRoot="$out/MeshHost"
$originalHost="$base/BodyOutfit/Host"
$smith='Characters/VillageBlacksmithNPC20261118'
$sourceRel="$smith/SK_Smith_Outfit.uasset"
$baseline='ABA9E3316685CE002BDA99C5E041C11E940D7FAFC52778F5F8D180A4C008FABC'
$hostContent="$hostRoot/Content"
$live="$project/Content/$sourceRel"
New-Item -ItemType Directory -Force -Path "$hostContent/$smith" | Out-Null
Copy-Item -LiteralPath "$originalHost/SmithBody.uproject" -Destination "$hostRoot/SmithPattern.uproject"
function Mount-SmithFolder($label,$src) {
    $dst=Join-Path $hostContent $label
    if(-not (Test-Path -LiteralPath $dst)){New-Item -ItemType Junction -Path $dst -Target $src | Out-Null}
}
Mount-SmithFolder 'AsianMale_Jason' "$project/Content/AsianMale_Jason"
Mount-SmithFolder 'Characters/ModularOutfit20260924' "$originalHost/Content/Characters/ModularOutfit20260924"
Mount-SmithFolder "$smith/BodyOutfit" "$project/Content/$smith/BodyOutfit"
if(-not (Test-Path -LiteralPath "$hostContent/$smith/SK_Smith_Body.uasset")){Copy-Item -LiteralPath "$project/Content/$smith/SK_Smith_Body.uasset" -Destination "$hostContent/$smith/SK_Smith_Body.uasset"}
if(-not (Test-Path -LiteralPath "$hostContent/$sourceRel")){
    if((Get-FileHash -LiteralPath $live).Hash -ne $baseline){throw 'The source workwear package changed.'}
    Copy-Item -LiteralPath $live -Destination "$hostContent/$sourceRel"
}
$env:UE_SKIP_UBT_SDK_SETUP='1'
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$hostRoot/SmithPattern.uproject" -run=pythonscript "-script=$PSScriptRoot/save_outfit.py" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$out/mesh_save.log" *> "$out/mesh_save.console.log"
if($LASTEXITCODE -ne 0){ throw "Workwear commandlet failed ($LASTEXITCODE)" }
$guard=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    try{$held=$guard.WaitOne()} catch [Threading.AbandonedMutexException]{$held=$true}
    $hash=(Get-FileHash -LiteralPath "$hostContent/$sourceRel").Hash
    $current=(Get-FileHash -LiteralPath $live).Hash
    if($current -ne $hash){
        $prior="$out/mesh_installed.json"
        $ours=if(Test-Path -LiteralPath $prior){(Get-Content -Raw -LiteralPath $prior|ConvertFrom-Json).hash}else{''}
        if($current -ne $baseline -and $current -ne $ours){throw 'Existing live workwear package was modified independently.'}
        $stage="$live.smithworkwear.tmp"
        [IO.File]::Copy("$hostContent/$sourceRel",$stage,$true)
        [IO.File]::Move($stage,$live,$true)
    }
    $receipt=Get-Content -Raw "$out/mesh_saved.json"|ConvertFrom-Json
    $receipt | Add-Member NoteProperty hash $hash
    $receipt | Add-Member NoteProperty previous_hash $baseline
    $receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$out/mesh_installed.json" -Encoding UTF8
}finally{if($held){$guard.ReleaseMutex()};$guard.Dispose()}

