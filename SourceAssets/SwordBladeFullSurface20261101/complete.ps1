$ErrorActionPreference='Stop'
try {
    & "$PSScriptRoot/build.ps1"
    & "$PSScriptRoot/run_asset_task.ps1" -Script 'install_materials.py'
    @{completed=$true;gameplay_tested=$false;editor_launched=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/completion.json" -Encoding utf8
} catch {
    @{completed=$false;error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/completion.json" -Encoding utf8
    throw
}
