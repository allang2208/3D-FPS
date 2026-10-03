$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'import_refinement_background_v3.ps1') -ScriptFile 'import_dormitory_variants_v2.py' -OutputFolder 'DormitoryVariantsV2'
