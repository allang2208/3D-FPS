param([string]$UnloadedStaffMapContext)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'import_refinement_background_v3.ps1') -ScriptFile 'import_room_details_v5.py' -OutputFolder 'RoomDetailsV5' -UnloadedStaffMapContext $UnloadedStaffMapContext
