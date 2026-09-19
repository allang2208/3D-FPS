# Apply the completed style through the editor that owns the loaded mesh.
# Does not rebuild native modules, start/stop PIE or run acceptance tests.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$bridge = Join-Path $projectRoot 'Tools/AssetPipeline/mcp_call_codex.ps1'
$mesh = '/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy.SK_FatZombie_Meshy'
$material = '/Game/Monsters/FatZombieMeshy/StyleV1/MI_FatZombie_Infected_V1.MI_FatZombie_Infected_V1'

function Invoke-StyleTool([string]$Toolset, [string]$Name, [hashtable]$Arguments) {
    $payload = @{toolset_name=$Toolset;tool_name=$Name;arguments=$Arguments} | ConvertTo-Json -Depth 18 -Compress
    $raw = & $bridge -Tool call_tool -ArgumentsJson $payload
    try { $result = $raw | ConvertFrom-Json } catch { throw ($raw -join "`n") }
    if ($result.returnValue -is [bool] -and !$result.returnValue) { throw "$Name failed: $raw" }
    return $result
}

$properties = Invoke-StyleTool 'editor_toolset.toolsets.object.ObjectTools' 'get_properties' @{
    instance=@{refPath=$mesh};properties=@('Materials')}
$slots = ($properties.returnValue | ConvertFrom-Json).Materials
$target = $slots | Where-Object {$_.materialSlotName -eq 'Material_002'}
if (!$target) { throw 'The expected FatZombie material slot is unavailable.' }
$previous = $target.materialInterface.refPath
$original = '/Game/Monsters/FatZombieMeshy/Materials/M_FatZombie_Meshy.M_FatZombie_Meshy'
if ($previous -ne $original -and $previous -ne $material) {
    throw "The FatZombie material was changed by another task: $previous"
}
# Preserve imported slot names, UV densities and overlay fields as well as the
# display slot name. The generic skeletal set_material helper drops some fields.
$target.materialInterface.refPath = $material
$values = @{Materials=@($slots)} | ConvertTo-Json -Depth 18 -Compress
$null = Invoke-StyleTool 'editor_toolset.toolsets.object.ObjectTools' 'set_properties' @{
    instance=@{refPath=$mesh};values=$values}
$null = Invoke-StyleTool 'editor_toolset.toolsets.asset.AssetTools' 'save_assets' @{asset_paths=@($mesh)}

@{
    revision='1.0';mesh=$mesh;slot='Material_002';previous_material=$previous;material=$material
    f6_entry='FatZombie';scope='Material slot assignment only'
    assets_saved=$true;runtime_tested=$false;preview_rendered=$false
} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $projectRoot 'SourceAssets/FatZombieStyleV1/activation.json') -Encoding UTF8
Write-Output 'FAT_STYLE_SAMPLE_ACTIVATED'
