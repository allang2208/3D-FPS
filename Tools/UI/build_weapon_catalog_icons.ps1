param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$outputRoot=Join-Path $projectRoot 'SourceAssets/WeaponInventoryIcons20260913'
New-Item -ItemType Directory -Force -Path "$outputRoot/before" | Out-Null
foreach($definition in @('ue_m1911','ue_akm','ue_m4a1')) {
    $sourceIcon=Join-Path $projectRoot "Content/ColdSteelData/Icons/$definition.png"
    $backupIcon=Join-Path $outputRoot "before/$definition.png"
    if((Test-Path -LiteralPath $sourceIcon) -and !(Test-Path -LiteralPath $backupIcon)) {
        Copy-Item -LiteralPath $sourceIcon -Destination $backupIcon
    }
}
# Production image export only: no map, player profile, inventory audit or gameplay session.
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$projectRoot/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -AllowCommandletRendering -NoTextureStreaming -unattended -nosplash -RenderOffscreen "-abslog=$outputRoot/export.log" *> "$outputRoot/export-console.log"
exit $LASTEXITCODE
