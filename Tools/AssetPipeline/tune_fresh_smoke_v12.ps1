# Author only the current smoke alpha curve through the running editor's API.
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$expressionPath = Join-Path $projectRoot 'SourceAssets/GunplayVFX20260914/SmokeAlphaV12.hlsl'
$alphaExpression = (Get-Content -LiteralPath $expressionPath) -join ' '
$smokePath = '/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeStreamV12.NS_FPS_MuzzleSmokeStreamV12'
$request = @{
    toolset_name = 'NiagaraToolsets.NiagaraToolset_System'
    tool_name = 'SetStackInputData'
    arguments = @{
        stackInputRef = @{
            system = @{ refPath = $smokePath }
            emitterName = 'Muzzle_Smoke'
            scriptName = 'ParticleUpdateScript'
            moduleName = 'ScaleColor'
            rendererIndex = -1
            inputNameStack = @('Scale Alpha')
        }
        inputData = @{
            struct = @{ refPath = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression' }
            value = @{ hlslExpression = $alphaExpression }
        }
    }
} | ConvertTo-Json -Depth 16 -Compress

function Invoke-SmokeAuthoringTool([string]$RequestJson) {
    $response = & (Join-Path $PSScriptRoot 'mcp_call.ps1') -Tool call_tool -ArgumentsJson $RequestJson | ConvertFrom-Json
    if ($response.error) { throw ($response.error | ConvertTo-Json -Compress) }
    if ($response.result.isError) { throw $response.result.content[0].text }
    return ($response.result.content[0].text | ConvertFrom-Json).returnValue
}

Invoke-SmokeAuthoringTool $request | Out-Null
$compileRequest = @{
    toolset_name = 'NiagaraToolsets.NiagaraToolset_System'
    tool_name = 'GetSystemCompileState'
    arguments = @{ system = @{ refPath = $smokePath } }
} | ConvertTo-Json -Depth 8 -Compress
$compileDeadline = [DateTime]::UtcNow.AddMinutes(2)
do {
    $state = Invoke-SmokeAuthoringTool $compileRequest
    if ($state.bHasErrors) { throw ($state | ConvertTo-Json -Depth 12 -Compress) }
    if (-not $state.bIsStale -and -not $state.bIsCompiling) { break }
    if ([DateTime]::UtcNow -ge $compileDeadline) { throw 'Smoke asset is still compiling; it has not been saved.' }
    Start-Sleep -Seconds 2
} while ($true)

$saveRequest = @{
    toolset_name = 'editor_toolset.toolsets.asset.AssetTools'
    tool_name = 'save_assets'
    arguments = @{ asset_paths = @('/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeStreamV12') }
} | ConvertTo-Json -Depth 8 -Compress
if (-not (Invoke-SmokeAuthoringTool $saveRequest)) { throw 'Could not save the smoke asset.' }
Write-Output 'GUNPLAY_V12_FRESH_SMOKE_SAVED peak_boost=20% gameplay_not_run'
