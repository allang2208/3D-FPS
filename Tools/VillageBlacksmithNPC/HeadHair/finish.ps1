$ErrorActionPreference='Stop'
$shop='D:/FPS3D/FPSGAME/SourceAssets/VillageBlacksmithNPC20261118'
if(-not ((Test-Path -LiteralPath "$shop/Meshy/head.glb") -or (Test-Path -LiteralPath "$shop/Meshy/CombinedR1/head.glb"))){throw "The commissioned Meshy GLB is required to fit the head."}
$master=Get-Item -LiteralPath "$shop/Meshy/CombinedR1/head.glb" -ErrorAction SilentlyContinue
if(-not $master){$master=Get-Item -LiteralPath "$shop/Meshy/head.glb"}
$surface=Get-Item -LiteralPath "$shop/HeadHair/game_surface.npz" -ErrorAction SilentlyContinue
if(-not $surface -or $surface.LastWriteTimeUtc -lt $master.LastWriteTimeUtc){
    & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python "$PSScriptRoot/reduce_master.py" *> "$shop/HeadHair/reduction.log"
    if($LASTEXITCODE -ne 0){throw "Game surface reduction failed ($LASTEXITCODE)."}
}
& python "$PSScriptRoot/prepare_head.py"
if($LASTEXITCODE -ne 0){throw "Head fitting failed ($LASTEXITCODE)."}
Remove-Item Env:SMITH_DESIGN_GROOM -ErrorAction SilentlyContinue
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python "$PSScriptRoot/author_hair.py" *> "$shop/HeadHair/author.log"
if($LASTEXITCODE -ne 0){throw "Groom authoring failed ($LASTEXITCODE)."}
& "$PSScriptRoot/save.ps1"
