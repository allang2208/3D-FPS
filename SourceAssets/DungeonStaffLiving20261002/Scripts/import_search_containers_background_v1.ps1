$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'import_refinement_background_v3.ps1') -ScriptFile 'import_search_containers_v1.py' -OutputFolder 'SearchContainersV1'
