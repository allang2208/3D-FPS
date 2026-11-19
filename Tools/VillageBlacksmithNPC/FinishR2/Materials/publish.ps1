$ErrorActionPreference = 'Stop'
$project='D:/FPS3D/FPSGAME'
$out="$project/SourceAssets/VillageBlacksmithNPC20261118/FinishR2/BodyOutfit"
$part='Characters/VillageBlacksmithNPC20261118/BodyOutfit'
$live="$project/Content/$part"
$source="$out/MaterialHost/Content/$part"
$initial=Get-Content -Raw -LiteralPath "$out/material_baseline.json" | ConvertFrom-Json -AsHashtable
$packages=(Get-Content -Raw -LiteralPath "$out/materials_saved.json" | ConvertFrom-Json).packages
$guard=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$guard.WaitOne() } catch [Threading.AbandonedMutexException] { $held=$true }
    $hashes=@{}
    $files=@()
    foreach($package in $packages) {
        $prefix="/Game/$part/"
        if (-not $package.StartsWith($prefix)) { throw "Unexpected destination $package" }
        $file=$package.Substring($prefix.Length)+'.uasset'
        if (-not ($file.StartsWith('SurfaceR2/') -or $initial.ContainsKey($file))) { throw "Unowned surface package $file" }
        $hashes[$file]=(Get-FileHash -LiteralPath "$source/$file").Hash
        if (Test-Path -LiteralPath "$live/$file") {
            $current=(Get-FileHash -LiteralPath "$live/$file").Hash
            if ($current -eq $hashes[$file]) { continue }
            if ($current -ne $initial[$file]) { throw "Concurrent material edit $file" }
        }
        $files+=$file
    }
    foreach($file in @($files|Sort-Object @{e={if($_.StartsWith('SurfaceR2/')){0}else{1}}})) {
        $dest="$live/$file"
        New-Item -ItemType Directory -Force (Split-Path -Parent $dest) | Out-Null
        $staged="$dest.surface-r2.tmp"
        [IO.File]::Copy("$source/$file",$staged,$true)
        [IO.File]::Move($staged,$dest,$true)
    }
    [ordered]@{packages=$hashes;reused_slots=@('Brass','Thread','Sole')} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$out/materials_installed.json" -Encoding utf8
} finally {if($held){$guard.ReleaseMutex()};$guard.Dispose()}
