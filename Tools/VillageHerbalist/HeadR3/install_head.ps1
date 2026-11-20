param([ValidateSet('Install','Baseline','Portrait','Studio')][string]$Stage = 'Install')
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$relative = 'SourceAssets/VillageHerbalist/FullBody/HeadR3'
$source = Join-Path $project $relative
$receipts = Join-Path $source 'UE'
$character = Join-Path $project 'Content/Characters/VillageHerbalist'
$target = Join-Path $character 'HeadR3'
$name = 'SK_VillageHerbalist_HeadR3'
$fbx = Join-Path $source "Assembly/$name.fbx"
$commandlet = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$stamp = [guid]::NewGuid().ToString('N')
$hostDir = Join-Path $project "Saved/HerbalistHeadR3/Studio/$stamp"
$snapshot = Join-Path $hostDir 'Content/Characters/VillageHerbalist'
$descriptor = Join-Path $hostDir 'LinZhi.uproject'
$env:LINZHI_R3_HOST = $hostDir
$env:UE_SKIP_UBT_SDK_SETUP = '1'
$utf8 = [Text.UTF8Encoding]::new($false)

if ($Stage -eq 'Install') {
    $marker = Join-Path $source 'Assembly/geometry-ready.json'
    if (!(Test-Path -LiteralPath $marker) -or !(Test-Path -LiteralPath $fbx)) {
        throw "Waiting for the final assembled FBX and its ready record at $source/Assembly"
    }
    $ready = Get-Content -Raw -LiteralPath $marker | ConvertFrom-Json
    $fbxHash = (Get-FileHash -LiteralPath $fbx).Hash
    if ($ready.fbx_sha256 -and $ready.fbx_sha256 -ne $fbxHash) { throw 'The assembled FBX no longer matches its ready record' }
    $receipt = Join-Path $receipts 'published.json'
    if (Test-Path -LiteralPath $target) {
        if ((Test-Path -LiteralPath $receipt) -and (Test-Path -LiteralPath "$target/$name.uasset")) {
            $old = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
            if ($old.fbx_sha256 -eq $fbxHash -and $old.mesh_sha256 -eq (Get-FileHash -LiteralPath "$target/$name.uasset").Hash) {
                Write-Output "Already published $target"
                return
            }
        }
        throw "The revision directory already exists: $target"
    }
    & python.exe "$PSScriptRoot/ue_surface.py" $source
    if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the generated PBR surfaces' }
} elseif ($Stage -in @('Portrait','Studio') -and !(Test-Path -LiteralPath "$target/$name.uasset")) {
    throw "Missing published mesh $target/$name.uasset"
}

New-Item -ItemType Directory -Path $snapshot,"$hostDir/Config" -Force | Out-Null
foreach ($item in @('SK_VillageHerbalist.uasset','SK_VillageHerbalist_Skeleton.uasset',
        'A_VillageHerbalist_Idle.uasset','A_VillageHerbalist_Walk.uasset','Materials','Textures')) {
    Copy-Item -LiteralPath (Join-Path $character $item) -Destination $snapshot -Recurse
}
@{FileVersion=3; EngineAssociation='5.8'; Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $descriptor -Encoding ascii
@('[/Script/Engine.RendererSettings]','r.Substrate=True','r.Substrate.ProjectGBufferFormat=0',
  '[/Script/WindowsTargetPlatform.WindowsTargetSettings]','DefaultGraphicsRHI=DefaultGraphicsRHI_DX12',
  '-D3D12TargetedShaderFormats=PCD3D_SM5','+D3D12TargetedShaderFormats=PCD3D_SM6',
  '[ConsoleVariables]','Interchange.FeatureFlags.Import.FBX=False') |
    Set-Content -LiteralPath "$hostDir/Config/DefaultEngine.ini" -Encoding ascii
$common = @('-run=pythonscript','-unattended','-nop4','-nosplash','-nosound','-Multiprocess',
    '-asyncskinnedassetcompilation=0','-asynctexturecompilation=0','-LocalDataCachePath=D:/FPS3D/DerivedDataCache',
    "-abslog=$hostDir/engine.log")
if ($Stage -ne 'Install') {
    $revision = if ($Stage -eq 'Studio') { 'studio' } elseif ($Stage -eq 'Portrait') { 'HeadR3' } else { 'FaceR2' }
    if ($Stage -in @('Portrait','Studio')) { Copy-Item -LiteralPath $target -Destination $snapshot -Recurse }
    $env:LINZHI_R3_REVISION = $revision
    $env:LINZHI_R3_SOFTBOX = if ($Stage -eq 'Studio') { '1' } else { '0' }
    $env:LINZHI_R3_PORTRAITS = if ($Stage -eq 'Studio') { "$hostDir/HDR" } else { Join-Path $source 'UE/Portraits' }
    & $commandlet $descriptor @common "-script=$PSScriptRoot/ue_portrait.py" -AllowCommandletRendering -RenderOffscreen -dx12 *> "$hostDir/console.log"
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath "$env:LINZHI_R3_PORTRAITS/$revision-saved-package.json")) {
        throw "Could not render the published model. See $hostDir/engine.log"
    }
    if ($Stage -eq 'Studio') {
        & python.exe "$PSScriptRoot/ue_match_portraits.py" $env:LINZHI_R3_PORTRAITS
        if ($LASTEXITCODE -ne 0) { throw 'Could not finish the tone-mapped studio portraits' }
    }
    Write-Output "Portraits: $source/UE/Portraits"
    return
}

$stagedSource = Join-Path $hostDir $relative
New-Item -ItemType Directory -Path "$stagedSource/Assembly","$stagedSource/UE" -Force | Out-Null
Copy-Item -LiteralPath $fbx -Destination "$stagedSource/Assembly"
Copy-Item -LiteralPath "$receipts/Textures" -Destination "$stagedSource/UE" -Recurse
Copy-Item -LiteralPath "$receipts/surfaces.json" -Destination "$stagedSource/UE"
& $commandlet $descriptor @common "-script=$PSScriptRoot/ue_author.py" -NullRHI *> "$hostDir/console.log"
if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath "$hostDir/authored.json")) {
    throw "Could not author HeadR3. See $hostDir/engine.log"
}
$authored = Get-Content -LiteralPath "$hostDir/authored.json" -Raw | ConvertFrom-Json
$mutex = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    if (Test-Path -LiteralPath $target) { throw "Another operation created $target while preparing the revision" }
    foreach ($dep in @('SK_VillageHerbalist.uasset','SK_VillageHerbalist_Skeleton.uasset')) {
        if ((Get-FileHash -LiteralPath "$snapshot/$dep").Hash -ne (Get-FileHash -LiteralPath "$character/$dep").Hash) {
            throw "The source body or skeleton changed during authoring: $dep"
        }
    }
    if ((Get-FileHash -LiteralPath $fbx).Hash -ne $fbxHash) { throw 'The assembled FBX changed during authoring' }
    # Publish the complete new folder in a single same-volume rename.
    $temporary = Join-Path $character ".HeadR3-$stamp"
    Copy-Item -LiteralPath "$snapshot/HeadR3" -Destination $temporary -Recurse
    $packages = @{}
    foreach ($pkg in $authored.saved_packages) {
        $prefix = '/Game/Characters/VillageHerbalist/HeadR3/'
        if (!$pkg.StartsWith($prefix) -or $pkg.Contains('..')) { throw "Unexpected package $pkg" }
        $leaf = $pkg.Substring($prefix.Length) + '.uasset'
        $packages[$pkg] = (Get-FileHash -LiteralPath (Join-Path $temporary $leaf)).Hash
    }
    [IO.Directory]::Move($temporary, $target)
    $record = @{authored=$authored; fbx_sha256=$fbxHash; mesh_sha256=$packages["/Game/Characters/VillageHerbalist/HeadR3/$name"];
        package_sha256=$packages; source=$fbx; work=$hostDir; saved_at=[DateTimeOffset]::Now.ToString('o')}
    [IO.File]::WriteAllText("$receipts/published-$stamp.tmp", ($record | ConvertTo-Json -Depth 12), $utf8)
    [IO.File]::Move("$receipts/published-$stamp.tmp", $receipt)
} finally {
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
Write-Output "Published $target"
