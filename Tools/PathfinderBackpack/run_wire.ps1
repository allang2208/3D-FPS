param([switch]$SkipBuild,[switch]$SkipNative)
$ErrorActionPreference='Stop'
# Compatibility entry: gravity and async preload remain enabled.
# The old fixed five-pack native fixture is no longer a prerequisite here.
& 'D:/FPS3D/FPSGAME/Tools/BackpackFit/run_network_review.ps1' -SkipBuild:$SkipBuild -Packs @('ue_pathfinder_backpack')
exit $LASTEXITCODE
