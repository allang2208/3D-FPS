$ErrorActionPreference = 'Stop'
$project='D:/FPS3D/FPSGAME'
$relative='Characters/VillageBlacksmithNPC20261118/SK_Smith_Outfit.uasset'
$out="$project/SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit"
$source="$out/Host/Content/$relative"
$dest="$project/Content/$relative"
$baseline='B7A4C36FCC5155F241E3E43CF0FFA2BFA4D41C40131A64E5DB1D023148E7CE84'
if(-not (Select-String -LiteralPath "$out/save_shirt_revision.log" -Pattern 'SMITH_REVISED_SHIRT_SAVED' -Quiet)){throw 'Missing revised package save receipt'}
$guard=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$guard.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    $expected=(Get-FileHash -LiteralPath $source).Hash
    if($expected -eq $baseline){throw 'Source did not change'}
    $current=(Get-FileHash -LiteralPath $dest).Hash
    if($current -ne $expected) {
        $previousStrap = Get-Content -LiteralPath "$out/shoulder_strap_baseline.txt" -ErrorAction SilentlyContinue
        if($current -ne $baseline -and $current -ne $previousStrap){throw 'Installed workwear was changed by another writer'}
        $staged="$dest.workshirt-tmp"
        [IO.File]::Copy($source,$staged,$true)
        [IO.File]::Move($staged,$dest,$true)
    }
    $receipt=[ordered]@{ asset='/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Outfit'; sha256=$expected; source_revision='fitted neck, crossing apron straps, short placket and rolled sleeves'; changed_utc=[DateTime]::UtcNow.ToString('o') }
    $receipt | ConvertTo-Json | Set-Content -LiteralPath "$out/workshirt_installed.json" -Encoding utf8
} finally {if($held){$guard.ReleaseMutex()};$guard.Dispose()}

