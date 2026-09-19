$ErrorActionPreference='Stop'
$mcp='D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call.ps1'
$get=@{toolset_name='ConfigSettingsToolset.ConfigSettingsToolset';tool_name='GetSectionPropertyValues';arguments=@{containerName='Project';categoryName='Plugins';sectionName='Python';propertyNames=@('bRemoteExecution')}}
$response=& $mcp -Tool call_tool -ArgumentsJson ($get | ConvertTo-Json -Depth 6 -Compress)
$parsed=$response | ConvertFrom-Json
$prior=(($parsed.result.content[0].text | ConvertFrom-Json).returnValue | ConvertFrom-Json).bRemoteExecution
if($null -eq $prior){throw 'Could not read the current editor Python connection setting.'}
function Set-EquipPythonConnection([bool]$Enabled){
    $argsObject=@{toolset_name='ConfigSettingsToolset.ConfigSettingsToolset';tool_name='SetSectionProperties';arguments=@{containerName='Project';categoryName='Plugins';sectionName='Python';propertiesJson=(@{bRemoteExecution=$Enabled}|ConvertTo-Json -Compress)}}
    & $mcp -Tool call_tool -ArgumentsJson ($argsObject | ConvertTo-Json -Depth 6 -Compress)
}
try {
    if(-not $prior){Set-EquipPythonConnection $true}
    & python (Join-Path $PSScriptRoot 'live_import_client.py')
    $importExit=$LASTEXITCODE
} finally {
    if(-not $prior){Set-EquipPythonConnection $false}
}
exit $importExit
