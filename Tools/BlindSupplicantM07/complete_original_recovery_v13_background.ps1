param()
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
$taskTools = Join-Path $taskRoot 'Tools/BlindSupplicantM07'
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor
& (Join-Path $taskTools 'run_import_background.ps1') -TaskScript (Join-Path $taskTools 'import_original_recovery_v13.py')
$taskReceiptPath = Join-Path $taskRoot 'SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV13/ue_delivery_v13.json'
$taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json
if (-not $taskReceipt.saved) { throw 'V13 assets and AI/F6 Blueprint have not all saved.' }
& 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe' (Join-Path $taskTools 'apply_original_recovery_native_v13.py')
if ($LASTEXITCODE -ne 0) { throw 'V13 native references did not update.' }
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor | Tee-Object -Variable taskEditorOutput
$taskEditorLine = @($taskEditorOutput | Where-Object { $_ -like 'M07 authoring binaries built:*' })[-1]
$taskEditorLog = $taskEditorLine.Substring('M07 authoring binaries built: '.Length)
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAME | Tee-Object -Variable taskGameOutput
$taskGameLine = @($taskGameOutput | Where-Object { $_ -like 'M07 authoring binaries built:*' })[-1]
$taskGameLog = $taskGameLine.Substring('M07 authoring binaries built: '.Length)
& 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe' (Join-Path $taskTools 'record_original_recovery_delivery_v13.py') --editor-log $taskEditorLog --game-log $taskGameLog
if ($LASTEXITCODE -ne 0) { throw 'V13 delivery record did not save.' }
Write-Output ('M07 V13 sources, assets, AI/F6 references and Editor/Game builds saved. Receipt=' + $taskReceiptPath + '. No GUI/game/test started.')
