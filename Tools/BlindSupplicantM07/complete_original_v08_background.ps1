param([switch]$RemakeSource)
$ErrorActionPreference = 'Stop'
$taskProjectRoot = 'D:/FPS3D/FPSGAME'
$taskTools = Join-Path $taskProjectRoot 'Tools/BlindSupplicantM07'
if ($RemakeSource) { & (Join-Path $taskTools 'produce_original_v08_source.ps1') }

# The saved V07 constructor dependencies stay active until V08 is saved.
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'run_import_background.ps1') -TaskScript (Join-Path $taskTools 'import_original_v08.py')
& (Join-Path $taskTools 'run_import_background.ps1') -TaskScript (Join-Path $taskTools 'repair_navigation_original_v08.py')
$taskReceiptPath = Join-Path $taskProjectRoot 'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV08/ue_original_delivery_v08.json'
$taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json
if (-not $taskReceipt.saved) { throw 'OriginalV08 packages are not saved; constructor defaults were left on the prior revision.' }
$taskNativeCpp = Join-Path $taskProjectRoot 'Source/FPSGAME/Monsters/BlindSupplicantMonster.cpp'
$taskNativeSource = [IO.File]::ReadAllText($taskNativeCpp)
[IO.File]::WriteAllText($taskNativeCpp, $taskNativeSource.Replace('SK_M07_OriginalV07','SK_M07_OriginalV08').Replace('AnimationsOriginalV07','AnimationsOriginalV08'), [Text.UTF8Encoding]::new($false))
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAME
Write-Output 'OriginalV08 source and saved AI/F6 assets produced. No GUI or game was started; user testing pending.'
