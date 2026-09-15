# Repair the active editor's fireball materials, compile on its real RHI, save only these assets.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$sourceRoot = Join-Path $projectRoot 'SourceAssets/FireballMotionHeat20260914'
$backupRoot = Join-Path $projectRoot 'trash/skills-magic-20260915/SourceAssets/FireballMotionHeat20260914/BeforeVelocityConflictFix'
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
$materialNames = @('M_FireballFluid_A','M_FireballFluid_B','M_FluidShortFlamesExposure','M_FluidThinWispMotion')
$materialFolder = '/Game/Skills/Fireball/FluidBurn20260914/'
$report = [ordered]@{ issue='OutputVelocity conflicts with DepthFade'; materials=@(); game_tested=$false }

function Invoke-FireballTool([string]$Toolset, [string]$Name, [hashtable]$Arguments) {
    $request = @{toolset_name=$Toolset;tool_name=$Name;arguments=$Arguments} | ConvertTo-Json -Depth 12 -Compress
    $response = & (Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call.ps1') -Tool call_tool -ArgumentsJson $request | ConvertFrom-Json
    if ($response.error) { throw ($response.error | ConvertTo-Json -Compress) }
    if ($response.result.isError) { throw $response.result.content[0].text }
    return ($response.result.content[0].text | ConvertFrom-Json).returnValue
}

foreach ($name in $materialNames) {
    $diskPath = Join-Path $projectRoot ('Content/Skills/Fireball/FluidBurn20260914/' + $name + '.uasset')
    $backupPath = Join-Path $backupRoot ($name + '.uasset')
    if (-not (Test-Path -LiteralPath $backupPath)) { Copy-Item -LiteralPath $diskPath -Destination $backupPath }
    $assetPath = $materialFolder + $name
    $reference = @{refPath=$assetPath + '.' + $name}
    $before = Invoke-FireballTool 'editor_toolset.toolsets.object.ObjectTools' 'get_properties' @{instance=$reference;properties=@('bOutputTranslucentVelocity','bDisableDepthTest','translucencyPass')}
    $changed = Invoke-FireballTool 'editor_toolset.toolsets.object.ObjectTools' 'set_properties' @{instance=$reference;values='{"bOutputTranslucentVelocity":false}'}
    if (-not $changed) { throw ('Could not update ' + $name) }
    Invoke-FireballTool 'editor_toolset.toolsets.material.MaterialTools' 'recompile' @{material_or_function=$reference} | Out-Null
    $saved = Invoke-FireballTool 'editor_toolset.toolsets.asset.AssetTools' 'save_assets' @{asset_paths=@($assetPath)}
    if (-not $saved) { throw ('Could not save ' + $name) }
    $report.materials += @{asset=$assetPath;before=$before;output_velocity=$false;compiled=$true;saved=$true}
    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $sourceRoot 'velocity-conflict-fix.json') -Encoding utf8
    Write-Output ('FIREBALL_MATERIAL_REPAIRED ' + $name)
}
Write-Output 'FIREBALL_VELOCITY_DEPTH_CONFLICT_FIXED'
