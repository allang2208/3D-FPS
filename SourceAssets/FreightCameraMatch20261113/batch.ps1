param([string]$SceneScript='capture.py')
$ErrorActionPreference='Stop'
$project='D:\FPS3D\FPSGAME'
$source=Join-Path $project 'SourceAssets\FreightWarehouseWeathering20261110\run_background.ps1'
$scriptBase=Split-Path $source
$runner=(Get-Content -Raw -LiteralPath $source).Replace('$taskMutex.WaitOne(5000)','$taskMutex.WaitOne()').Replace('$PSScriptRoot','$scriptBase').Replace("'-nullrhi'","'-AllowCommandletRendering' '-RenderOffscreen' '-d3d12'").Replace('Receipts/import-', '../FreightCameraMatch20261113/job-').Replace('Receipts/stdout-', '../FreightCameraMatch20261113/stdout-').Replace('Receipts/live-save-','../FreightCameraMatch20261113/live-')
& ([scriptblock]::Create($runner)) -ScriptName ('../FreightCameraMatch20261113/'+$SceneScript)
