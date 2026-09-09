$ErrorActionPreference = 'Stop'

$Headers = @{
    Accept = 'application/json, text/event-stream'
    'Content-Type' = 'application/json'
}

function Invoke-McpRequest($Body) {
    $Response = Invoke-WebRequest `
        -Uri 'http://127.0.0.1:8000/mcp' `
        -Method Post `
        -Headers $Headers `
        -Body ($Body | ConvertTo-Json -Depth 80)
    return $Response.Content | ConvertFrom-Json
}

$InitializeBody = @{
    jsonrpc = '2.0'
    id = 1
    method = 'initialize'
    params = @{
        protocolVersion = '2025-06-18'
        capabilities = @{}
        clientInfo = @{ name = 'fps-weather-config'; version = '1.0' }
    }
}
$InitializeResponse = Invoke-WebRequest `
    -Uri 'http://127.0.0.1:8000/mcp' `
    -Method Post `
    -Headers $Headers `
    -Body ($InitializeBody | ConvertTo-Json -Depth 10)
$Headers['Mcp-Session-Id'] = [string]($InitializeResponse.Headers['Mcp-Session-Id'] | Select-Object -First 1)
Invoke-McpRequest @{ jsonrpc = '2.0'; method = 'notifications/initialized'; params = @{} } | Out-Null

$script:RequestId = 1
function Invoke-ToolsetCall {
    param(
        [string] $Toolset,
        [string] $ToolName,
        [hashtable] $Arguments
    )
    $script:RequestId++
    $Response = Invoke-McpRequest @{
        jsonrpc = '2.0'
        id = $script:RequestId
        method = 'tools/call'
        params = @{
            name = 'call_tool'
            arguments = @{
                toolset_name = $Toolset
                tool_name = $ToolName
                arguments = $Arguments
            }
        }
    }
    if (-not $Response.result) {
        throw "No MCP result returned for $ToolName"
    }
    if ($Response.result.isError) {
        throw $Response.result.content.text
    }
    Write-Output "OK $ToolName"
}

$NiagaraToolset = 'NiagaraToolsets.NiagaraToolset_System'
$AssetToolset = 'editor_toolset.toolsets.asset.AssetTools'
$FloatType = @{ classStructOrEnum = @{ refPath = '/Script/Niagara.NiagaraFloat' } }
$FloatStruct = @{ refPath = '/Script/Niagara.NiagaraFloat' }

function Add-RuntimeVariables($System) {
    Invoke-ToolsetCall $NiagaraToolset 'AddUserVariables' @{
        system = $System
        variablesToAdd = @(
            @{
                name = 'User.SpawnRate'
                description = 'Runtime spawn rate controlled by FPSWeatherManager'
                type = $FloatType
                defaultValue = @{ struct = $FloatStruct; value = @{ value = 0.0 } }
            },
            @{
                name = 'User.RainIntensity'
                description = 'Normalized runtime rain intensity'
                type = $FloatType
                defaultValue = @{ struct = $FloatStruct; value = @{ value = 0.0 } }
            }
        )
    }
}

function New-StackReference {
    param(
        [hashtable] $System,
        [string] $EmitterName,
        [string] $ScriptName,
        [string] $ModuleName,
        [string[]] $InputNames = @()
    )
    return @{
        system = $System
        emitterName = $EmitterName
        scriptName = $ScriptName
        moduleName = $ModuleName
        rendererIndex = -1
        inputNameStack = @($InputNames)
    }
}

function Set-StackValue {
    param(
        [hashtable] $Reference,
        [string] $StructPath,
        [hashtable] $Value
    )
    Invoke-ToolsetCall $NiagaraToolset 'SetStackInputData' @{
        stackInputRef = $Reference
        inputData = @{ struct = @{ refPath = $StructPath }; value = $Value }
    }
}

$Rain = @{ refPath = '/Game/Weather/VFX/NS_FPS_Rain.NS_FPS_Rain' }
Add-RuntimeVariables $Rain
Set-StackValue `
    (New-StackReference $Rain 'RainDrops' 'EmitterUpdateScript' 'SpawnRate' @('SpawnRate')) `
    '/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked' `
    @{ linkedVariable = @{ name = 'User.SpawnRate'; type = $FloatType } }
Set-StackValue (New-StackReference $Rain 'RainDrops' 'ParticleSpawnScript' 'InitializeParticle' @('Lifetime Min')) '/Script/Niagara.NiagaraFloat' @{ value = 1.1 }
Set-StackValue (New-StackReference $Rain 'RainDrops' 'ParticleSpawnScript' 'InitializeParticle' @('Lifetime Max')) '/Script/Niagara.NiagaraFloat' @{ value = 1.35 }
Set-StackValue (New-StackReference $Rain 'RainDrops' 'ParticleSpawnScript' 'InitializeParticle' @('Color')) '/Script/CoreUObject.LinearColor' @{ r = 0.36; g = 0.58; b = 0.9; a = 0.72 }
Set-StackValue `
    (New-StackReference $Rain 'RainDrops' 'ParticleSpawnScript' 'InitializeParticle' @('Sprite Size Mode')) `
    '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum' `
    @{ enum = @{ refPath = '/Niagara/Enums/ENiagara_SizeScaleMode.ENiagara_SizeScaleMode' }; enumName = 'NewEnumerator4'; displayName = 'Non-Uniform' }
Set-StackValue (New-StackReference $Rain 'RainDrops' 'ParticleSpawnScript' 'InitializeParticle' @('Sprite Size')) '/Script/CoreUObject.Vector2f' @{ x = 2.2; y = 70.0 }
Set-StackValue `
    (New-StackReference $Rain 'RainDrops' 'ParticleSpawnScript' 'ShapeLocation' @('Shape Primitive')) `
    '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum' `
    @{ enum = @{ refPath = '/Niagara/Enums/Location/ENiagara_LocationShapes.ENiagara_LocationShapes' }; enumName = 'NewEnumerator2'; displayName = 'Box / Plane' }
Set-StackValue (New-StackReference $Rain 'RainDrops' 'ParticleSpawnScript' 'ShapeLocation' @('Box Size')) '/Script/CoreUObject.Vector3f' @{ x = 3200.0; y = 3200.0; z = 600.0 }
Set-StackValue (New-StackReference $Rain 'RainDrops' 'ParticleUpdateScript' 'GravityForce' @('Gravity')) '/Script/CoreUObject.Vector3f' @{ x = 180.0; y = 60.0; z = -2400.0 }
foreach ($ModuleName in @('AerodynamicDrag', 'Collision', 'WindForce', 'AlignParticlesWithCollisionPlane')) {
    Invoke-ToolsetCall $NiagaraToolset 'SetModuleEnabled' @{
        moduleRef = New-StackReference $Rain 'RainDrops' 'ParticleUpdateScript' $ModuleName
        bEnabled = $false
    }
}
Invoke-ToolsetCall $NiagaraToolset 'SetEmitterData' @{
    emitter = New-StackReference $Rain 'RainDrops' '' ''
    emitterData = @{ propertyValues = '{"bLocalSpace":true,"SimTarget":"GPUComputeSim"}' }
}
Invoke-ToolsetCall $NiagaraToolset 'SetRendererData' @{
    renderer = @{
        system = $Rain; emitterName = 'RainDrops'; scriptName = ''; moduleName = ''
        rendererIndex = 0; inputNameStack = @()
    }
    rendererData = @{ propertyValues = '{"Alignment":"VelocityAligned","FacingMode":"FaceCamera","bCastShadows":false,"bSortOnlyWhenTranslucent":true}' }
}

$Splashes = @{ refPath = '/Game/Weather/VFX/NS_FPS_RainSplashes.NS_FPS_RainSplashes' }
Add-RuntimeVariables $Splashes
Set-StackValue `
    (New-StackReference $Splashes 'RainSplashes' 'EmitterUpdateScript' 'SpawnRate' @('SpawnRate')) `
    '/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked' `
    @{ linkedVariable = @{ name = 'User.SpawnRate'; type = $FloatType } }
Set-StackValue (New-StackReference $Splashes 'RainSplashes' 'ParticleSpawnScript' 'InitializeParticle' @('Lifetime Min')) '/Script/Niagara.NiagaraFloat' @{ value = 0.18 }
Set-StackValue (New-StackReference $Splashes 'RainSplashes' 'ParticleSpawnScript' 'InitializeParticle' @('Lifetime Max')) '/Script/Niagara.NiagaraFloat' @{ value = 0.35 }
Set-StackValue (New-StackReference $Splashes 'RainSplashes' 'ParticleSpawnScript' 'InitializeParticle' @('Color')) '/Script/CoreUObject.LinearColor' @{ r = 0.5; g = 0.7; b = 1.0; a = 0.7 }
Set-StackValue (New-StackReference $Splashes 'RainSplashes' 'ParticleSpawnScript' 'InitializeParticle' @('Uniform Sprite Size Min')) '/Script/Niagara.NiagaraFloat' @{ value = 4.0 }
Set-StackValue (New-StackReference $Splashes 'RainSplashes' 'ParticleSpawnScript' 'InitializeParticle' @('Uniform Sprite Size Max')) '/Script/Niagara.NiagaraFloat' @{ value = 10.0 }
Set-StackValue `
    (New-StackReference $Splashes 'RainSplashes' 'ParticleSpawnScript' 'ShapeLocation' @('Shape Primitive')) `
    '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum' `
    @{ enum = @{ refPath = '/Niagara/Enums/Location/ENiagara_LocationShapes.ENiagara_LocationShapes' }; enumName = 'NewEnumerator2'; displayName = 'Box / Plane' }
Set-StackValue (New-StackReference $Splashes 'RainSplashes' 'ParticleSpawnScript' 'ShapeLocation' @('Box Size')) '/Script/CoreUObject.Vector3f' @{ x = 3000.0; y = 3000.0; z = 20.0 }
Set-StackValue (New-StackReference $Splashes 'RainSplashes' 'ParticleSpawnScript' 'AddVelocity' @('Velocity Speed')) '/Script/Niagara.NiagaraFloat' @{ value = 180.0 }
Set-StackValue (New-StackReference $Splashes 'RainSplashes' 'ParticleSpawnScript' 'AddVelocity' @('Cone Axis')) '/Script/CoreUObject.Vector3f' @{ x = 0.0; y = 0.0; z = 1.0 }
Set-StackValue (New-StackReference $Splashes 'RainSplashes' 'ParticleUpdateScript' 'GravityForce' @('Gravity')) '/Script/CoreUObject.Vector3f' @{ x = 0.0; y = 0.0; z = -980.0 }
Set-StackValue (New-StackReference $Splashes 'RainSplashes' 'ParticleUpdateScript' 'Drag' @('Drag')) '/Script/Niagara.NiagaraFloat' @{ value = 2.5 }
Invoke-ToolsetCall $NiagaraToolset 'SetEmitterData' @{
    emitter = New-StackReference $Splashes 'RainSplashes' '' ''
    emitterData = @{ propertyValues = '{"bLocalSpace":true}' }
}
Invoke-ToolsetCall $NiagaraToolset 'SetRendererData' @{
    renderer = @{
        system = $Splashes; emitterName = 'RainSplashes'; scriptName = ''; moduleName = ''
        rendererIndex = 0; inputNameStack = @()
    }
    rendererData = @{ propertyValues = '{"FacingMode":"FaceCamera","bCastShadows":false,"bSortOnlyWhenTranslucent":true}' }
}

# The targeted save helper in UE 5.8 currently rejects valid Niagara object paths.
# Saving all dirty content packages uses the engine's native loading/saving utility.
Invoke-ToolsetCall $AssetToolset 'save_assets' @{ asset_paths = @() }

$WeatherParameters = @{ refPath = '/Game/Weather/Materials/MPC_FPS_Weather.MPC_FPS_Weather' }
Invoke-ToolsetCall 'editor_toolset.toolsets.object.ObjectTools' 'set_properties' @{
    instance = $WeatherParameters
    values = '{"ScalarParameters":[{"ParameterName":"WeatherWetness","DefaultValue":0.0},{"ParameterName":"WeatherCloudiness","DefaultValue":0.12},{"ParameterName":"WeatherLightning","DefaultValue":0.0}]}'
}
Invoke-ToolsetCall $AssetToolset 'save_assets' @{ asset_paths = @() }
