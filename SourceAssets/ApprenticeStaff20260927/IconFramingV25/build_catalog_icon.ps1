# Produce only the staff inventory artwork through the same studio as live icons.
param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
    throw 'Close the editor before offline staff icon production. No processes were stopped.'
}
$icon=Join-Path $projectRoot 'Content/ColdSteelData/Icons/ue_apprentice_staff.png'
$legacy=Join-Path $projectRoot 'Content/ColdSteelData/Icons/apprentice_staff.png'
foreach($source in @($icon,$legacy)) {
    $backup=Join-Path $PSScriptRoot ('Before/Content/ColdSteelData/Icons/'+[IO.Path]::GetFileName($source))
    if((Test-Path -LiteralPath $source) -and !(Test-Path -LiteralPath $backup)) {
        New-Item -ItemType Directory -Force -Path (Split-Path $backup -Parent) | Out-Null
        Copy-Item -LiteralPath $source -Destination $backup
    }
}
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$projectRoot/FPSGAME.uproject" `
    -run=ColdSteelWeaponIconCatalog -Definition=ue_apprentice_staff `
    -AllowCommandletRendering -NoTextureStreaming -unattended -nop4 -nosplash -nosound -RenderOffscreen `
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
    "-abslog=$PSScriptRoot/catalog-export.log" *> "$PSScriptRoot/catalog-export-console.log"
if($LASTEXITCODE -ne 0) { throw "Staff catalog authoring failed: $LASTEXITCODE" }
# Old saved data and consumers of ue_icon still use this path. Keep one image.
Copy-Item -LiteralPath $icon -Destination $legacy -Force
$receipt=[ordered]@{
    definition='ue_apprentice_staff'; complete=$true; icon=$icon; legacy_alias=$legacy
    sha256=(Get-FileHash -LiteralPath $icon -Algorithm SHA256).Hash
    source='UE inventory icon studio / factory modular assembly'; runtime_tested=$false
}
$receipt | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'icon-receipt.json') -Encoding UTF8
Write-Output 'Staff inventory artwork saved, including the legacy filename alias.'
