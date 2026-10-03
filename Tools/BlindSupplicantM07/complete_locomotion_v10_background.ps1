param()
$ErrorActionPreference = 'Stop'
$taskProjectRoot = 'D:/FPS3D/FPSGAME'
$taskTools = Join-Path $taskProjectRoot 'Tools/BlindSupplicantM07'
& (Join-Path $taskTools 'run_import_background.ps1') -TaskScript (Join-Path $taskTools 'import_locomotion_v10.py')
$taskReceipt = Get-Content -LiteralPath (Join-Path $taskProjectRoot 'SourceAssets/BlindSupplicantM07Meshy20261001/LocomotionV10/ue_locomotion_delivery_v10.json') -Raw | ConvertFrom-Json
if (-not $taskReceipt.saved) { throw 'V10 locomotion packages are not saved; native defaults remain intact.' }
$taskNativePath = Join-Path $taskProjectRoot 'Source/FPSGAME/Monsters/BlindSupplicantMonster.cpp'
$taskNativeSource = [IO.File]::ReadAllText($taskNativePath)
foreach ($taskRole in @('SlowWalk', 'Chase')) {
    $taskOldPath = 'AnimationsOriginalV08/A_M07_' + $taskRole
    $taskNewPath = 'AnimationsLocomotionV10/A_M07_' + $taskRole
    $taskNativeSource = $taskNativeSource.Replace($taskOldPath, $taskNewPath)
}
[IO.File]::WriteAllText($taskNativePath, $taskNativeSource, [Text.UTF8Encoding]::new($false))
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAME
Write-Output 'V10 two locomotion clips, AI/F6 Blueprint and native defaults saved and built. No GUI, game or test was started.'
