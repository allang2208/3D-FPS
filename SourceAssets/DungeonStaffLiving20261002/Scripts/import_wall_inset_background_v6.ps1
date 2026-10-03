param([string]$UnloadedStaffMapContext)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'import_refinement_background_v3.ps1') -ScriptFile 'import_wall_inset_v6.py' -OutputFolder 'WallInsetV6' -UnloadedStaffMapContext $UnloadedStaffMapContext
