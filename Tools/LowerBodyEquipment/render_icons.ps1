$ErrorActionPreference = 'Stop'
$taskProject = 'D:/FPS3D/FPSGAME'
$taskEngine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
foreach ($item in @('ue_jeans','ue_cargo_pants','ue_casual_sneakers')) {
    & $taskEngine "$taskProject/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog "-Definition=$item" -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -Multiprocess "-abslog=$taskProject/SourceAssets/LowerBodyEquipment20261003/icon-$item-resident.log" *> "$taskProject/SourceAssets/LowerBodyEquipment20261003/icon-$item-resident-console.txt"
    if ($LASTEXITCODE -ne 0) { throw "Icon production failed: $item; see the item log." }
    Write-Output "LOWER_BODY_ICON_SAVED $item"
}
