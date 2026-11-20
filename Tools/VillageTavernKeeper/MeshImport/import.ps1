param([Parameter(Mandatory)][ValidateSet('surface','character')][string]$Stage)
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$output = Join-Path $project 'SourceAssets/VillageTavernKeeper/FullBody/UEAuthoringR1'
$hostRoot = Join-Path $project 'Saved/TavernKeeperMeshAuthoring/Host'
$descriptor = Join-Path $hostRoot 'TavernKeeperMesh.uproject'
foreach ($path in @($output, "$hostRoot/Content/Characters/VillageTavernKeeper", "$hostRoot/Config")) {
    New-Item -Path $path -ItemType Directory -Force | Out-Null
}
@{
    FileVersion=3
    EngineAssociation='5.8'
    Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $descriptor -Encoding ascii
@'
[/Script/Engine.RendererSettings]
r.Substrate=True
r.Substrate.ProjectGBufferFormat=0
[ConsoleVariables]
Interchange.FeatureFlags.Import.FBX=False
'@ | Set-Content -LiteralPath "$hostRoot/Config/DefaultEngine.ini" -Encoding ascii

if ($Stage -eq 'surface') {
    & python "$PSScriptRoot/prepare_surface.py"
} else {
    & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python-exit-code 1 --python "$PSScriptRoot/prepare_rig.py" *> "$output/prepare_rig.log"
}
if ($LASTEXITCODE -ne 0) { throw "Could not prepare $Stage, exit $LASTEXITCODE" }
$env:TAVERN_KEEPER_IMPORT_STAGE = $Stage
$env:UE_SKIP_UBT_SDK_SETUP = '1'
$commandlet = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
& $commandlet $descriptor -run=pythonscript "-script=$PSScriptRoot/save_assets.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -asyncskinnedassetcompilation=0 -asynctexturecompilation=0 '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$output/$Stage-engine.log" *> "$output/$Stage-console.log"
if ($LASTEXITCODE -ne 0) { throw "UE $Stage import exited $LASTEXITCODE. See $output/$Stage-engine.log" }
$packages = Get-Content -LiteralPath "$output/${Stage}_saved.json" -Raw | ConvertFrom-Json
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    # Publish dependencies before the mesh, with its skeleton as the last readiness signal.
    foreach ($package in @($packages | Sort-Object { [int]$_.EndsWith('_Skeleton') })) {
        if (!$package.StartsWith('/Game/Characters/VillageTavernKeeper/') -or $package.Contains('..')) {
            throw "Unexpected package $package"
        }
        $relative = $package.Substring('/Game/'.Length) + '.uasset'
        $source = Join-Path "$hostRoot/Content" $relative
        $target = Join-Path "$project/Content" $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null
        if (Test-Path -LiteralPath $target) {
            if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $target).Hash) { throw "An existing package differs: $target" }
            continue
        }
        $temporary = "$target.innkeeper-$PID.tmp"
        [IO.File]::Copy($source, $temporary, $true)
        [IO.File]::Move($temporary, $target)
    }
    $packages | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$output/${Stage}_installed.json" -Encoding utf8
} finally {
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
Write-Output "Installed $Stage packages: $($packages -join ', ')"
