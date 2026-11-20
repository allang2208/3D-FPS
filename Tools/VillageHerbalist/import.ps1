$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$body = Join-Path $project 'SourceAssets/VillageHerbalist/FullBody'
$out = Join-Path $body 'UEAuthoringR1'
$work = Join-Path $project ('Saved/VillageHerbalistAuthoring/' + [guid]::NewGuid().ToString('N'))
$descriptor = Join-Path $work 'Herbalist.uproject'
$blender = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
$commandlet = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$python = (Get-Command python.exe -CommandType Application | Select-Object -First 1).Source
if (!(Test-Path -LiteralPath "$body/MeshyR1/model.glb")) { throw "Missing Meshy model in $body/MeshyR1" }
if (!(Test-Path -LiteralPath "$body/RigR1/rigged.glb") -and !(Test-Path -LiteralPath "$body/RigR1/rigged.fbx")) {
    throw "Missing Meshy skin in $body/RigR1"
}
New-Item -Path $out,"$work/Content/Characters/VillageHerbalist","$work/Config" -ItemType Directory -Force | Out-Null
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
'@ | Set-Content -LiteralPath "$work/Config/DefaultEngine.ini" -Encoding ascii
& $python "$PSScriptRoot/prepare_surface.py"
if ($LASTEXITCODE -ne 0) { throw "Could not extract herbalist materials, exit $LASTEXITCODE" }
& $blender --background --factory-startup --python-exit-code 1 --python "$PSScriptRoot/prepare_rig.py" *> "$work/blender.log"
if ($LASTEXITCODE -ne 0) { throw "Could not export Meshy skin, see $work/blender.log" }

$env:HERBALIST_HOST = $work
$env:HERBALIST_PYTHON = $python
$env:UE_SKIP_UBT_SDK_SETUP = '1'
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    & $commandlet $descriptor -run=pythonscript "-script=$PSScriptRoot/save_ue.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -asyncskinnedassetcompilation=0 -asynctexturecompilation=0 '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$work/engine.log" *> "$work/console.log"
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath "$work/saved.json")) {
        throw "Could not save herbalist asset packages, see $work/engine.log"
    }
    $packages = @(Get-Content -LiteralPath "$work/saved.json" -Raw | ConvertFrom-Json)
    $staged = @()
    foreach ($package in $packages) {
        if (!$package.StartsWith('/Game/Characters/VillageHerbalist/') -or $package.Contains('..')) {
            throw "Unexpected package $package"
        }
        $relative = $package.Substring('/Game/'.Length) + '.uasset'
        $source = Join-Path "$work/Content" $relative
        $target = Join-Path "$project/Content" $relative
        if (Test-Path -LiteralPath $target) {
            if ((Get-FileHash -LiteralPath $source).Hash -ne (Get-FileHash -LiteralPath $target).Hash) {
                throw "Existing package differs: $target. New authoring output is in $work"
            }
        } else {
            $staged += @{source=$source; target=$target}
        }
    }
    foreach ($file in $staged) {
        $target = $file.target
        New-Item -Path (Split-Path -Parent $target) -ItemType Directory -Force | Out-Null
        $temporary = "$target.herbalist-$PID.tmp"
        [IO.File]::Copy($file.source, $temporary, $true)
        [IO.File]::Move($temporary, $target)
    }
    Copy-Item -LiteralPath "$work/saved.json" -Destination "$out/installed.json"
} finally {
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
Write-Output "Installed herbalist packages $($packages -join ', ')"
