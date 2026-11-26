$ErrorActionPreference = 'Stop'
$project = 'D:/FPS3D/FPSGAME'
$out = "$project/SourceAssets/VillageBlacksmithNPC20261118/FinishR2/BodyOutfit"
$studio = "$out/MaterialHost"
$parts = 'Characters/VillageBlacksmithNPC20261118/BodyOutfit'
$live = "$project/Content/$parts"
$source = "$studio/Content/$parts"
New-Item -ItemType Directory -Force "$source/Materials","$source/SurfaceR2" | Out-Null
if (-not(Test-Path -LiteralPath "$source/Textures")) {
    New-Item -ItemType Junction "$source/Textures" -Target "$live/Textures" | Out-Null
}
Copy-Item -LiteralPath "$project/SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit/Host/SmithBody.uproject" -Destination "$studio/SmithSurface.uproject" -Force
$slots = @('Linen','Twill','Apron','Saddle','Boot')
$receipt = "$out/material_baseline.json"
if (-not (Test-Path -LiteralPath $receipt)) {
    $initial = @{}
    foreach ($name in $slots) {
        $file="Materials/M_Smith_$name.uasset"
        $initial[$file]=(Get-FileHash -LiteralPath "$live/$file").Hash
        Copy-Item -LiteralPath "$live/$file" -Destination "$source/$file"
    }
    $initial | ConvertTo-Json | Set-Content -LiteralPath $receipt -Encoding utf8
}
$env:UE_SKIP_UBT_SDK_SETUP='1'
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$studio/SmithSurface.uproject" -run=pythonscript "-script=$PSScriptRoot/save_materials.py" -unattended -nop4 -nosplash -nosound -NullRHI "-LocalDataCachePath=D:/FPS3D/DerivedDataCache" "-abslog=$out/surface_save.log" *> "$out/surface_console.log"
if ($LASTEXITCODE -ne 0) { throw "Surface import exited $LASTEXITCODE" }
& "$PSScriptRoot/publish.ps1"

