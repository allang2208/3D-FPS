# User-requested diagnostic. Runs a copied native module and isolated saves;
# content/plugin junctions are read-only inputs, never recursively clean this host.
param([switch]$WaitForEntry,[switch]$CaptureTrees,[switch]$AuditDisappearance,[switch]$FrameAudit,[switch]$PIE,[string]$ModulePath='',
    [ValidatePattern('^[A-Za-z0-9_]+$')][string]$ProfileSourceSlot='')
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$run = Join-Path $project ('Saved/VegetationStreamingCheck/' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$hostPath = Join-Path $run 'Host'
New-Item -ItemType Directory -Path "$hostPath/Binaries/Win64", "$run/Saved/SaveGames" -Force | Out-Null
Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$hostPath/FPSGAME.uproject"
Copy-Item -LiteralPath "$project/Config" -Destination "$hostPath/Config" -Recurse
# -UserDir relocates ProjectIntermediateDir as well as Saved. Put the registry
# cache where this host actually reads it; otherwise PIE rescans all content.
New-Item -ItemType Directory -Path "$run/Intermediate" -Force | Out-Null
foreach ($name in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin') {
    $cache = Join-Path $project "Intermediate/$name"
    if (Test-Path -LiteralPath $cache) { Copy-Item -LiteralPath $cache -Destination "$run/Intermediate/$name" -Recurse }
}
foreach ($folder in 'Content','Plugins') {
    New-Item -ItemType Junction -Path (Join-Path $hostPath $folder) -Target (Join-Path $project $folder) | Out-Null
}
foreach ($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules') {
    $source = "$project/Binaries/Win64/$file"
    if ($file -eq 'UnrealEditor-FPSGAME.dll' -and $ModulePath) { $source = $ModulePath }
    Copy-Item -LiteralPath $source -Destination "$hostPath/Binaries/Win64/$file"
}
Copy-Item -LiteralPath "$project/Saved/SaveGames/TemperateHills_World.sav" -Destination "$run/Saved/SaveGames/TemperateHills_World.sav"
$profileInputs = @()
if ($ProfileSourceSlot) {
    foreach ($suffix in '_A.sav','_A.sha1','_B.sav','_B.sha1') {
        $source = "$project/Saved/SaveGames/$ProfileSourceSlot$suffix"
        if (-not (Test-Path -LiteralPath $source)) { throw "Profile input missing: $source" }
        $target = "$run/Saved/SaveGames/ColdSteel_VegetationStreamingCheck$suffix"
        Copy-Item -LiteralPath $source -Destination $target
        $profileInputs += @{ source=$source; copy=$target; sha256=(Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash }
    }
}
$nativeHash = (Get-FileHash -LiteralPath "$hostPath/Binaries/Win64/UnrealEditor-FPSGAME.dll" -Algorithm SHA256).Hash
$captureWidth=1280
$captureHeight=720
if ($FrameAudit) {
    $userSettings="$project/Saved/Config/WindowsEditor/GameUserSettings.ini"
    if (Test-Path -LiteralPath $userSettings) {
        New-Item -ItemType Directory -Path "$run/Saved/Config/WindowsEditor" -Force | Out-Null
        Copy-Item -LiteralPath $userSettings -Destination "$run/Saved/Config/WindowsEditor/GameUserSettings.ini"
        $settingsText=Get-Content -LiteralPath $userSettings -Raw
        if ($settingsText -match '(?m)^ResolutionSizeX=(\d+)') { $captureWidth=[int]$Matches[1] }
        if ($settingsText -match '(?m)^ResolutionSizeY=(\d+)') { $captureHeight=[int]$Matches[1] }
    }
}
$checkCommand = 'fps.Test.HillsVegetationStreaming'
$auditConsole = if ($FrameAudit) { 'pcg.RuntimeGeneration.EnableDebugging 1,' } else { '' }
if ($WaitForEntry) { $checkCommand = 'py ' + "$project/Tools/WorldGeneration/observe_hills_entry.py" }
if ($PIE) { $checkCommand = 'py ' + "$project/Tools/WorldGeneration/start_hills_pie_audit.py" }
$testArgs = @(
    ('"' + "$hostPath/FPSGAME.uproject" + '"'), '/Game/GameMaps/L_TemperateHills_Initial',
    '-game','-RenderOffscreen','-windowed',"-ResX=$captureWidth","-ResY=$captureHeight",'-unattended','-nosound','-nosplash',
    '-ClearwaterNoMenu','-SkipStartupMenu','-HillsVegetationCheck','-ColdSteelProfile=VegetationStreamingCheck',
    '-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
    '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
    ('-UserDir="' + $run + '"'),('-abslog="' + "$run/check.log" + '"'),
    ('-ExecCmds="t.MaxFPS 45,' + $auditConsole + $checkCommand + '"'),
    '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False'
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bAutoSaveEnable=False'
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False'
)
$previousSdkSetting = $env:UE_SKIP_UBT_SDK_SETUP
if ($CaptureTrees) { $testArgs += '-HillsVegetationCapture' }
if ($AuditDisappearance) { $testArgs += '-HillsVegetationAudit' }
if ($FrameAudit) { $testArgs += '-HillsVegetationFrameAudit' }
if ($PIE) { $testArgs = @($testArgs | Where-Object { $_ -ne '-game' }); $testArgs += '-HillsPIEAudit' }
try {
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    $testProcess = Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $testArgs -WindowStyle Hidden -PassThru
} finally { $env:UE_SKIP_UBT_SDK_SETUP = $previousSdkSetting }
@{ pid=$testProcess.Id; run=$run; module_sha256=$nativeHash; args=$testArgs; profile_inputs=$profileInputs } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$run/launch.json" -Encoding utf8
Write-Output "VEGETATION_CHECK_PID=$($testProcess.Id)"
Write-Output "VEGETATION_CHECK_RUN=$run"
