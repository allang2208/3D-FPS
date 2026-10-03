param()
$ErrorActionPreference = 'Stop'
$taskProjectRoot = 'D:/FPS3D/FPSGAME'
$taskTools = Join-Path $taskProjectRoot 'Tools/BlindSupplicantM07'
# The V11 package must use the repaired V09 cloth capture path and its own
# body collision package. Compile that native authoring before import.
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'run_import_background.ps1') -TaskScript (Join-Path $taskTools 'import_original_hands_v11.py')
$taskReceiptPath = Join-Path $taskProjectRoot 'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryHandsV11/ue_hand_arm_delivery_v11.json'
$taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json
if (-not $taskReceipt.saved) { throw 'V11 original hand/arm model, cloth, collision, actions and AI/F6 Blueprint are not all saved.' }
$taskNativePath = Join-Path $taskProjectRoot 'Source/FPSGAME/Monsters/BlindSupplicantMonster.cpp'
$taskNativeSource = [IO.File]::ReadAllText($taskNativePath)
$taskNativeSource = $taskNativeSource.Replace('SK_M07_OriginalV09.SK_M07_OriginalV09', 'SK_M07_OriginalV11.SK_M07_OriginalV11')
$taskNativeSource = $taskNativeSource.Replace('/AnimationsOriginalV08/', '/AnimationsOriginalV11/')
$taskNativeSource = $taskNativeSource.Replace('/AnimationsLocomotionV10/', '/AnimationsOriginalV11/')
[IO.File]::WriteAllText($taskNativePath, $taskNativeSource, [Text.UTF8Encoding]::new($false))
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAME
Write-Output ('V11 original hand/arm model, matching corrected reference, twelve actions and AI/F6 references saved. Native Editor/Game defaults built. Receipt=' + $taskReceiptPath + '. No GUI, game or test was started.')
