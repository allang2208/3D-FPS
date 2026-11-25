param(
    [string]$Art = 'F:/FPSGAMEData/ArtProduction/HillsVillageWindmill/GameR1',
    [string]$Engine = 'E:/Program Files (x86)/UE_5.8',
    [switch]$YardOnly,
    [switch]$ImportYardAssets
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$run = Join-Path $Art ('LevelHost/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$stage = Join-Path $run 'Host'
$binary = Join-Path $stage 'Binaries/Win64'
$cache = 'F:/FPSGAMEData/Caches/DerivedDataCache'
$env:WINDMILL_ART = $Art
$env:WINDMILL_PROJECT = $project
$env:WINDMILL_YARD_ONLY = [int]$YardOnly.IsPresent
$env:WINDMILL_IMPORT_YARD = [int]$ImportYardAssets.IsPresent
$env:WINDMILL_LEVEL_RUN = $run
$env:UE_SKIP_UBT_SDK_SETUP = '1'
if (!$YardOnly) {
    $import = Get-Content -Raw -LiteralPath "$Art/imported.json" | ConvertFrom-Json
    if (-not $import.complete) { throw 'The windmill mesh import is still in progress.' }
}
$gate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    if ($YardOnly) {
        . (Join-Path $PSScriptRoot '../VillageCarpenter/YardDetail/stage_host.ps1')
        $private=@('WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap','WorldGeneration/TemperateHills/VillageWindmill/Yard')
        $contentTarget=@((Get-Item -LiteralPath "$project/Content").Target)[0]
        $null=New-YardAuthorHost $project $run $contentTarget $private
    } else {
        New-Item -ItemType Directory -Force -Path $binary | Out-Null
        Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination $stage
        Copy-Item -Recurse -LiteralPath "$project/Config" -Destination $stage
        foreach ($name in 'Content','Plugins','Shaders') {
            New-Item -ItemType Junction -Path "$stage/$name" -Target "$project/$name" | Out-Null
        }
        foreach ($name in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules') {
            Copy-Item -LiteralPath "$project/Binaries/Win64/$name" -Destination $binary
        }
    }
    $argsList = @(('"'+$stage+'/FPSGAME.uproject"'), '/Engine/Maps/Entry', '-run=pythonscript',
        ('-script="'+$PSScriptRoot+'/save_windmill_level.py"'), '-unattended','-NullRHI','-nosplash',
        '-nosound','-nop4','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        '-ini:Engine:[ConsoleVariables]:Interchange.FeatureFlags.Import.FBX=False',
        ('-LocalDataCachePath='+$cache), ('-ZenDataPath='+$cache+'/Zen'),
        ('-ini:Engine:[VirtualTextureChunkDDCCache]:Path='+$cache+'/VT'), ('-abslog="'+$run+'/engine.log"'),
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    $process = Start-Process -FilePath "$Engine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath "$run/level-saved.json")) {
        Get-Content -LiteralPath "$run/engine.log" -Tail 40
        throw "Village level save did not complete. $run/engine.log"
    }
    if (!$YardOnly) { Get-Content -LiteralPath "$Art/level-saved.json" }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
if ($YardOnly) {
    $publish = Join-Path $run 'publish.py'
    @"
import sys
from pathlib import Path
sys.path.insert(0,r'$PSScriptRoot')
from publish_mill_yard import publish
publish(Path(r'$project'),Path(r'$Art'),Path(r'$run'))
"@ | Set-Content -LiteralPath $publish -Encoding utf8NoBOM
    $publishGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
    $ownsPublish=$false
    try {
        try { $ownsPublish=$publishGate.WaitOne() } catch [Threading.AbandonedMutexException] { $ownsPublish=$true }
        # Offscreen reviews also use UnrealEditor.exe. Only a production editor
        # can own this project's packages or serve its publishing bridge.
        $projectFile=[IO.Path]::GetFullPath((Join-Path $project 'FPSGAME.uproject'))
        $useBridge=[bool]@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {
            $match=[regex]::Match([string]$_.CommandLine,'(?i)(?:"([^"]+\.uproject)"|(?:^|\s)([^\s"]+\.uproject))(?=\s|$)')
            $candidate=($match.Groups[1].Value+$match.Groups[2].Value)
            !$match.Success -or ![IO.Path]::IsPathFullyQualified($candidate) -or [IO.Path]::GetFullPath($candidate) -eq $projectFile
        })
        if (!$useBridge) { & python $publish }
    } finally {
        if ($ownsPublish) { $publishGate.ReleaseMutex() }
        $publishGate.Dispose()
    }
    if ($useBridge) {
        & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $publish -OutputFile "$run/bridge.json" -MaxOutputChars 1600 -QueueWaitSeconds 300
    }
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath "$run/published.json")) { throw "Mill yard staged at $run; publication pending." }
    Get-Content -LiteralPath "$run/published.json" -Tail 8
}
