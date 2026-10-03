param([string]$UnloadedStaffMapContext)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'import_refinement_background_v3.ps1') -ScriptFile 'import_scene_polish_v4.py' -OutputFolder 'ScenePolishV4' -UnloadedStaffMapContext $UnloadedStaffMapContext
