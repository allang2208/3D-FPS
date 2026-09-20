# Produce the M16's transparent catalog PNG with the shared inventory studio.
# No gameplay session or package save; the commandlet writes only this PNG.
param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$sourceIcon=Join-Path $projectRoot 'Content/ColdSteelData/Icons/ue_m16a2.png'
$backupIcon=Join-Path $PSScriptRoot 'before/ue_m16a2.png'
if(!(Test-Path -LiteralPath $backupIcon)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backupIcon) | Out-Null
    Copy-Item -LiteralPath $sourceIcon -Destination $backupIcon
}
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$projectRoot/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -Definition=ue_m16a2 -AllowCommandletRendering -NoTextureStreaming -unattended -nosplash -RenderOffscreen '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$PSScriptRoot/catalog-export.log" *> "$PSScriptRoot/catalog-export-console.log"
exit $LASTEXITCODE
