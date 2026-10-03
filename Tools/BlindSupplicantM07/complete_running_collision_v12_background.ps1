param()
$ErrorActionPreference = 'Stop'
$taskRoot = 'D:/FPS3D/FPSGAME'
$taskTools = Join-Path $taskRoot 'Tools/BlindSupplicantM07'
# Source edits and both external authoring jobs must be complete before this
# single Editor build and asset import. This never opens an editor or game.
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor | Tee-Object -Variable taskEditorOutput
$taskEditorLine = @($taskEditorOutput | Where-Object { $_ -like 'M07 authoring binaries built:*' })[-1]
$taskEditorLog = $taskEditorLine.Substring('M07 authoring binaries built: '.Length)
& (Join-Path $taskTools 'run_import_background.ps1') -TaskScript (Join-Path $taskTools 'import_running_collision_v12.py')
$taskReceiptPath = Join-Path $taskRoot 'SourceAssets/BlindSupplicantM07Meshy20261001/RunningCollisionV12/ue_running_collision_delivery_v12.json'
$taskReceipt = Get-Content -LiteralPath $taskReceiptPath -Raw | ConvertFrom-Json
if (-not $taskReceipt.saved) { throw 'M07 V12 model, cloth collision, run/walk clips, speeds and AI/F6 Blueprint have not all saved.' }
& 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe' (Join-Path $taskTools 'apply_running_collision_native_v12.py')
if ($LASTEXITCODE -ne 0) { throw 'M07 V12 native default references could not be updated.' }
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAMEEditor | Tee-Object -Variable taskEditorOutput
$taskEditorLine = @($taskEditorOutput | Where-Object { $_ -like 'M07 authoring binaries built:*' })[-1]
$taskEditorLog = $taskEditorLine.Substring('M07 authoring binaries built: '.Length)
& (Join-Path $taskTools 'build_editor.ps1') -TargetName FPSGAME | Tee-Object -Variable taskGameOutput
$taskGameLine = @($taskGameOutput | Where-Object { $_ -like 'M07 authoring binaries built:*' })[-1]
$taskGameLog = $taskGameLine.Substring('M07 authoring binaries built: '.Length)
& 'C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe' (Join-Path $taskTools 'record_running_collision_delivery_v12.py') --editor-log $taskEditorLog --game-log $taskGameLog
if ($LASTEXITCODE -ne 0) { throw 'M07 V12 native production record could not be saved.' }
Write-Output ('M07 V12 assets, speeds and AI/F6 references saved. Native Editor/Game defaults built. Receipt=' + $taskReceiptPath + '. No GUI/game/test started.')
