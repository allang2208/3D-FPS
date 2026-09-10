param([string]$Editor='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')
# Compatibility entry: the visual shell has been replaced by the live profile and spatial inventory.
& (Join-Path $PSScriptRoot 'run_inventory_acceptance.ps1') -Editor $Editor
