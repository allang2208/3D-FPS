param([string]$UnloadedStaffMapContext)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'import_refinement_background_v3.ps1') -ScriptFile 'import_coffee_polish_v7.py' -OutputFolder 'CoffeePolishV7' -UnloadedStaffMapContext $UnloadedStaffMapContext
