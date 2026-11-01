param([switch]$StageOnly,[switch]$PublishOnly)
$ErrorActionPreference='Stop'
$m24Units=@('M24Attachments.cpp','FPSGAMECharacterProfile.cpp','ColdSteelIconResources.cpp',
    'ColdSteelWeaponIcons.cpp','M4GunsmithLayout.cpp','M4GunsmithOverview.cpp','ShotgunAttachmentAuditCommandlet.cpp')
& "$PSScriptRoot/../M24DualOptic20261029/build_incremental.ps1" -StageOnly:$StageOnly -PublishOnly:$PublishOnly `
    -CompileUnits $m24Units -OutputDirectory "$PSScriptRoot/Build"
