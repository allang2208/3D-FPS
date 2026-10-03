$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'import_refinement_background_v3.ps1') -ScriptFile 'import_container_open_parts_v3.py' -OutputFolder 'ContainerOpenPartsV3'
