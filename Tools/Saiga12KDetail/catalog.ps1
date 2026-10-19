$ErrorActionPreference='Stop'
$detailRoot='D:/FPS3D/FPSGAME'
$detailOut="$detailRoot/SourceAssets/Saiga12KDetail20261018"
while(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealEditor.exe' -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -notmatch '\s-game(?:\s|$)') }).Count -gt 0) { Start-Sleep -Seconds 10 }
$detailCatalog="$detailRoot/Content/ColdSteelData/Icons/ue_saiga12k.png"
if(-not (Test-Path -LiteralPath "$detailOut/SourceBefore/ue_saiga12k.png")){Copy-Item -LiteralPath $detailCatalog -Destination "$detailOut/SourceBefore/ue_saiga12k.png"}
$detailPreviousSdk=[Environment]::GetEnvironmentVariable('UE_SKIP_UBT_SDK_SETUP','Process')
try {
 [Environment]::SetEnvironmentVariable('UE_SKIP_UBT_SDK_SETUP','1','Process')
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$detailRoot/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -AllowCommandletRendering -NoTextureStreaming -unattended -nosplash -nosound -RenderOffscreen -Definition=ue_saiga12k "-abslog=$detailOut/Receipts/catalog.log" *> "$detailOut/Receipts/catalog-console.log"
 $detailCode=$LASTEXITCODE
} finally { [Environment]::SetEnvironmentVariable('UE_SKIP_UBT_SDK_SETUP',$detailPreviousSdk,'Process') }
@{complete=($detailCode -eq 0);exit_code=$detailCode;definition='ue_saiga12k';render_offscreen=$true;gameplay_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$detailOut/Receipts/catalog.json" -Encoding utf8
if($detailCode -ne 0){throw "Catalog failed $detailCode"}
Copy-Item -LiteralPath $detailCatalog -Destination "$detailOut/Preview/UE_Catalog.png"
