param([string]$UnloadedStaffMapContext)
& "$PSScriptRoot/import_refinement_background_v3.ps1" -ScriptFile 'import_intact_tiles_v4.py' -OutputFolder 'IntactTilesV4' -UnloadedStaffMapContext $UnloadedStaffMapContext
