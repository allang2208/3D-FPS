$ErrorActionPreference="Stop"
$project="D:/FPS3D/FPSGAME"
$data="$project/SourceAssets/VillageBlacksmithNPC20261118/HeadHair"
$hostRoot="$data/AuthoringHost"
$receipt = Get-Content -Raw "$data/saved.json" | ConvertFrom-Json
$sourcePrefix = [IO.Path]::GetFullPath("$hostRoot/Content")
$targetPrefix = [IO.Path]::GetFullPath("$project/Content")
$ownedList = @($receipt.assets)
# Install only new, individually-owned packages, preserving other NPC pieces and existing editor state.
    foreach($entry in $ownedList) {
        if(-not $entry.StartsWith('/Game/Characters/VillageBlacksmithNPC20261118/')){throw "Unexpected package $entry"}
        $relative = $entry.Substring('/Game/'.Length)+'.uasset'
        $source = Join-Path $sourcePrefix $relative
        $target = Join-Path $targetPrefix $relative
        if(-not (Test-Path -LiteralPath $source)){throw "Missing saved package $source"}
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
        if(Test-Path -LiteralPath $target) {
            if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $target).Hash){throw "Existing package collision at $target"}
        } else { [IO.File]::Copy($source,$target,$false) }
    }
    $receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath "$data/installed.json" -Encoding utf8
