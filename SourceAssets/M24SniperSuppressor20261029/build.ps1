param([switch]$StageOnly,[switch]$PublishOnly)
& "$PSScriptRoot/../M24DualOptic20261029/build_incremental.ps1" -StageOnly:$StageOnly -PublishOnly:$PublishOnly -CompileUnits @('ColdSteelIconResources.cpp','ColdSteelWeaponIcons.cpp') -OutputDirectory $PSScriptRoot.Replace('\','/')
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
