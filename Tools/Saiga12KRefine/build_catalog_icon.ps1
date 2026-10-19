$ErrorActionPreference='Stop'
$saigaRoot='D:/FPS3D/FPSGAME'
$saigaOut="$saigaRoot/SourceAssets/Saiga12KRefine20261017/Receipts"
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$saigaRoot/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -AllowCommandletRendering -NoTextureStreaming -unattended -nosplash -nosound -RenderOffscreen -Definition=ue_saiga12k "-abslog=$saigaOut/catalog-icon.log" *> "$saigaOut/catalog-icon-console.log"
$saigaExit=$LASTEXITCODE
Write-Output "Catalog image production exit: $saigaExit"
exit $saigaExit