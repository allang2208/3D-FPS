# Apply the scoped material/blueprint adjustment through the running editor.
# No C++ build, gameplay launch or automated visual test.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$bridge = Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1'
$materialPath = '/Game/Monsters/ZombieDog/RefinedWoundsV5/Materials/M_ZombieDog_RefinedWounds.M_ZombieDog_RefinedWounds'
$blueprintPath = '/Game/Monsters/ZombieDog/V1/BP_ZombieDog.BP_ZombieDog'

function Invoke-WoundTool([string]$Toolset, [string]$Name, [hashtable]$Arguments) {
    $payload = @{toolset_name=$Toolset;tool_name=$Name;arguments=$Arguments} | ConvertTo-Json -Depth 20 -Compress
    $raw = & $bridge -Tool call_tool -ArgumentsJson $payload
    try { $result = $raw | ConvertFrom-Json } catch { throw ($raw -join "`n") }
    if ($result.PSObject.Properties.Name -contains 'returnValue' -and $result.returnValue -is [bool] -and !$result.returnValue) {
        throw "$Name failed: $raw"
    }
    return $result
}

# Resolve existing nodes rather than rebuild a live material or touch its MIs.
$expressions = Invoke-WoundTool 'editor_toolset.toolsets.material.MaterialTools' 'get_expressions' @{
    material_or_function=@{refPath=$materialPath}}
$field = $null
foreach ($expression in $expressions.returnValue) {
    if ($expression.refPath -notmatch ':MaterialExpressionCustom_') { continue }
    $properties = Invoke-WoundTool 'editor_toolset.toolsets.object.ObjectTools' 'get_properties' @{
        instance=$expression;properties=@('Code')}
    $values = $properties.returnValue | ConvertFrom-Json
    if ($values.Code -match 'float4 Centers\[8\]' -and $values.Code -match 'FurRemoval') {
        $field = $expression; break
    }
}
if (!$field) { throw 'Could not locate the existing zombie dog wound field' }
$componentResponse = Invoke-WoundTool 'editor_toolset.toolsets.object.ObjectTools' 'get_properties' @{
    instance=@{refPath=$blueprintPath};properties=@('WoundAppearance')}
$componentPath = ($componentResponse.returnValue | ConvertFrom-Json).WoundAppearance.refPath
if (!$componentPath) { throw 'Zombie dog has no wound appearance component' }

$shader = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'refined_wound_field.hlsl') -Raw -Encoding UTF8
$null = Invoke-WoundTool 'editor_toolset.toolsets.object.ObjectTools' 'set_properties' @{
    instance=@{refPath=$field.refPath}; values=(@{Code=$shader} | ConvertTo-Json -Compress)}
$null = Invoke-WoundTool 'editor_toolset.toolsets.material.MaterialTools' 'recompile' @{
    material_or_function=@{refPath=$materialPath}}
$null = Invoke-WoundTool 'editor_toolset.toolsets.object.ObjectTools' 'set_properties' @{
    instance=@{refPath=$componentPath};values='{"MinWounds":6,"MaxWounds":8}'}
$null = Invoke-WoundTool 'editor_toolset.toolsets.asset.AssetTools' 'save_assets' @{
    asset_paths=@($materialPath,$blueprintPath)}

$record = @{
    revision='5.1';material=$materialPath;blueprint=$blueprintPath;target_wounds=@(6,8)
    main_length_scale=1.65;secondary_length_scale=1.75;width_scale=2.0;depth_envelope_scale=1.30
    mask_strength_scale=1.22;method='editor MCP material field and blueprint defaults'
    assets_saved=$true;runtime_tested=$false;preview_rendered=$false
}
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $projectRoot 'SourceAssets/ZombieDogRefinedWoundsV5/visibility_v51.json') -Encoding UTF8
Write-Output 'ZOMBIE_DOG_WOUND_VISIBILITY_V51_SAVED'
