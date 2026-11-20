$ErrorActionPreference = 'Stop'
$project = (Resolve-Path "$PSScriptRoot/../..").Path
$stage = "$project/Saved/VillageBakerAuthoringR1"
$env:BAKER_UE_HOST = $stage
$env:UE_SKIP_UBT_SDK_SETUP = '1'
$pref = "$project/SourceAssets/JasonStrong20261117/AuthoringHost"
$engine = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$blender = 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe'
New-Item -ItemType Directory -Force -Path "$stage/Content/Characters/VillageBaker","$stage/Config" | Out-Null
foreach($mount in @('AsianMale_Jason','Characters/ModularOutfit20260924')) {
    $source = if ($mount -eq 'AsianMale_Jason') { "$project/Content/$mount" } else { "$pref/Content/$mount" }
    if (!(Test-Path -LiteralPath "$stage/Content/$mount")) {
        New-Item -ItemType Junction -Path "$stage/Content/$mount" -Target $source | Out-Null
    }
}
$descriptor = "$stage/BakerAuthoring.uproject"
$plugins = (Get-Content -LiteralPath "$pref/JasonAuthoring.uproject" -Raw | ConvertFrom-Json).Plugins
@{FileVersion=3;EngineAssociation='5.8';Plugins=$plugins} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $descriptor -Encoding ascii
@'
[/Script/Engine.RendererSettings]
r.Substrate=True
r.Substrate.ProjectGBufferFormat=0
'@ | Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding ascii
if (!(Test-Path -LiteralPath "$stage/geometry.json.gz")) {
    & $blender --background --factory-startup --python-exit-code 1 --python "$PSScriptRoot/import_geometry.py" *> "$stage/geometry.log"
    if($LASTEXITCODE -ne 0) { throw "FBX extraction failed, see $stage/geometry.log" }
}
if (!(Test-Path -LiteralPath "$stage/saved.json")) {
    & $engine $descriptor -run=pythonscript "-script=$PSScriptRoot/import_ue.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -asyncskinnedassetcompilation=0 -asynctexturecompilation=0 '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$stage/engine.log" *> "$stage/console.log"
    if (!(Test-Path -LiteralPath "$stage/saved.json")) { throw "Failed to save baker assets (exit $LASTEXITCODE). See $stage/engine.log" }
}
$receipt = Get-Content -LiteralPath "$stage/saved.json" -Raw | ConvertFrom-Json
$gameFolder = Join-Path "$project/Content/Characters" 'VillageBaker'
# All-new packages can be installed like other offline deliverables when there is
# no interactive editor. Publish the whole folder atomically, without replacing
# any existing package. Updates retain the serialized path below.
if (!(Test-Path -LiteralPath $gameFolder) -and !(Get-Process UnrealEditor -ErrorAction SilentlyContinue)) {
    $stageRoot = (Resolve-Path "$project/Content/Characters").Path
    $fresh = [IO.Path]::GetFullPath((Join-Path $stageRoot ('.VillageBaker-' + [Guid]::NewGuid().ToString('N'))))
    $gameFolder = [IO.Path]::GetFullPath($gameFolder)
    if ((Split-Path -Parent $fresh) -ne $stageRoot -or
        (Split-Path -Parent $gameFolder) -ne (Resolve-Path "$project/Content/Characters").Path) {
        throw "Unexpected baker publication paths."
    }
    foreach ($package in $receipt.packages) {
        $prefix = '/Game/Characters/VillageBaker/'
        if (!$package.StartsWith($prefix) -or $package.Contains('..')) { throw "Unowned package $package" }
        $part = $package.Substring($prefix.Length) + '.uasset'
        $dest = Join-Path $fresh $part
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
        [IO.File]::Copy((Join-Path "$stage/Content/Characters/VillageBaker" $part), $dest, $false)
    }
    [IO.Directory]::Move($fresh, $gameFolder)
    Copy-Item -LiteralPath "$stage/saved.json" -Destination "$stage/installed.json"
    Write-Output "Installed $($receipt.packages.Count) new baker packages including $($receipt.mesh)"
    return
}
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    $publish = @()
    foreach ($package in $receipt.packages) {
        if (!$package.StartsWith('/Game/Characters/VillageBaker/') -or $package.Contains('..')) { throw "Unowned package $package" }
        $relative = $package.Substring(6) + '.uasset'
        $source = "$stage/Content/$relative"
        $target = "$project/Content/$relative"
        if (Test-Path -LiteralPath $target) {
            if ((Get-FileHash -LiteralPath $target).Hash -ne (Get-FileHash -LiteralPath $source).Hash) {
                throw "A different baker asset occupies $target."
            }
        } else { $publish += [PSCustomObject]@{Source=$source;Target=$target} }
    }
    foreach ($file in $publish) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $file.Target) | Out-Null
        $tmp = "$($file.Target).baker-$PID.tmp"
        [IO.File]::Copy($file.Source, $tmp, $true)
        [IO.File]::Move($tmp, $file.Target)
    }
    Copy-Item -LiteralPath "$stage/saved.json" -Destination "$stage/installed.json"
    Write-Output "Installed $($receipt.packages.Count) baker packages including $($receipt.mesh)"
} finally { if ($held) { $mutex.ReleaseMutex() }; $mutex.Dispose() }
