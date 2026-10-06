$ErrorActionPreference = 'Stop'
$taskProject = 'D:/FPS3D/FPSGAME'
$taskEngine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$taskRecords = "$taskProject/SourceAssets/BootsEquipment20261004"
$taskBusy = Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','dotnet.exe','cl.exe') }
if ($taskBusy) { throw 'An editor or build is active. Use the existing editor bridge or wait for the build before this background batch.' }
& $taskEngine "$taskProject/FPSGAME.uproject" -run=pythonscript "-script=$taskProject/Tools/BootsEquipment/save_assets.py" -NullRHI -unattended -nop4 -nosplash -Multiprocess "-abslog=$taskRecords/save-assets.log" *> "$taskRecords/save-assets-console.txt"
if ($LASTEXITCODE -ne 0) { throw 'Boots asset authoring failed; see save-assets.log.' }
Write-Output 'BOOTS_ASSET_SAVE_COMPLETE'
& py -3.11 "$taskProject/Tools/BootsEquipment/publish_catalog.py"
if ($LASTEXITCODE -ne 0) { throw 'Boots catalog publication failed.' }
& $taskEngine "$taskProject/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -Definition=ue_boots -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -Multiprocess "-abslog=$taskRecords/icon-ue_boots.log" *> "$taskRecords/icon-ue_boots-console.txt"
if ($LASTEXITCODE -ne 0) { throw 'Boots icon production failed; see icon-ue_boots.log.' }
Write-Output 'BOOTS_ICON_SAVED ue_boots'
