param([switch]$StageBaselineOnly)
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$body = Join-Path $project 'SourceAssets/VillageHerbalist/FullBody'
$face = Join-Path $body 'FaceR2'
$name = 'SK_VillageHerbalist'
$character = Join-Path $project 'Content/Characters/VillageHerbalist'
$ready = Join-Path $face 'mesh-ready.json'
$fbx = Join-Path $face "$name.fbx"
if ($StageBaselineOnly) {
    $fbx = Join-Path "$body/UEAuthoringR1" "$name.fbx"
} elseif (!(Test-Path -LiteralPath $ready -PathType Leaf) -or !(Test-Path -LiteralPath $fbx -PathType Leaf)) {
    throw "Awaiting $fbx and $ready"
}
if (!$StageBaselineOnly) {
    $definition = Get-Content -LiteralPath $ready -Raw -Encoding UTF8 | ConvertFrom-Json
    $hash = (Get-FileHash -LiteralPath $fbx).Hash
    if ($definition.fbx_sha256 -ne $hash) { throw 'The ready record and FBX have different hashes' }
    $receipt = Join-Path $face 'mesh_delivery.json'
    if (Test-Path -LiteralPath $receipt) {
        $old = Get-Content -LiteralPath $receipt -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($old.fbx_sha256 -eq $hash -and $old.package_sha256 -eq (Get-FileHash -LiteralPath "$character/$name.uasset").Hash) {
            Write-Output "Already saved $character/$name.uasset"
            return
        }
    }
}
$work = Join-Path $project ('Saved/HerbalistFaceReview/MeshInstall/' + [guid]::NewGuid().ToString('N'))
$stageSource = Join-Path $work 'SourceAssets/VillageHerbalist/FullBody/FaceR2'
$stageCharacter = Join-Path $work 'Content/Characters/VillageHerbalist'
$descriptor = Join-Path $work 'FaceMesh.uproject'
$cmdlet = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$unicode = [Text.UTF8Encoding]::new($false)
New-Item -ItemType Directory -Path $stageSource,$stageCharacter,"$work/Config" -Force | Out-Null
@{FileVersion=3; EngineAssociation='5.8'; Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $descriptor -Encoding ascii
@('[/Script/Engine.RendererSettings]','r.Substrate=True','r.Substrate.ProjectGBufferFormat=0',
  '[ConsoleVariables]','Interchange.FeatureFlags.Import.FBX=False') |
    Set-Content -LiteralPath "$work/Config/DefaultEngine.ini" -Encoding ascii
[IO.File]::Copy($fbx, "$stageSource/$name.fbx")
$job = @{fbx=(Get-FileHash -LiteralPath "$stageSource/$name.fbx").Hash}
if (!$StageBaselineOnly) {
    $job.ready = (Get-FileHash -LiteralPath $ready).Hash
    if ($definition.fbx_sha256 -ne $job.fbx) {
        throw 'The ready record and FBX have different hashes'
    }
}
foreach ($item in @("$name.uasset", "${name}_Skeleton.uasset", 'Materials', 'Textures')) {
    Copy-Item -LiteralPath (Join-Path $character $item) -Destination $stageCharacter -Recurse
}
$job.mesh = (Get-FileHash -LiteralPath "$stageCharacter/$name.uasset").Hash
$job.skeleton = (Get-FileHash -LiteralPath "$stageCharacter/${name}_Skeleton.uasset").Hash
[IO.File]::WriteAllText("$work/job.json", ($job | ConvertTo-Json), $unicode)
$env:HERBALIST_MESH_HOST = $work
$env:UE_SKIP_UBT_SDK_SETUP = '1'
Write-Output "Authoring in $work"
& $cmdlet $descriptor -run=pythonscript "-script=$PSScriptRoot/install_face_mesh_stage.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -asyncskinnedassetcompilation=0 -asynctexturecompilation=0 '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$work/engine.log" *> "$work/console.log"
if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath "$work/staged.json")) {
    throw "Could not author the mesh. See $work/engine.log"
}
if ($StageBaselineOnly) { Write-Output "Prepared baseline in $work"; return }
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    $live = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match '(?i)FPSGAME[.]uproject' })
    $publisher = (Join-Path $PSScriptRoot 'install_face_mesh_publish.py').Replace('\','/') | ConvertTo-Json -Compress
    $location = $work.Replace('\','/') | ConvertTo-Json -Compress
    $interactive = if ($live.Count) { 'True' } else { 'False' }
    $wrapper = "import runpy`nrunpy.run_path($publisher)['publish']($location, $interactive)`n"
    [IO.File]::WriteAllText("$work/publish.py", $wrapper, $unicode)
    if ($live.Count) {
        & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$work/publish.py" -QueueWaitSeconds 300 -OutputFile "$work/bridge.log" -MaxOutputChars 1700
    } else {
        & python.exe -I "$work/publish.py"
    }
    if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath "$work/published.json")) {
        throw "Mesh publication did not complete. Staged package remains in $work"
    }
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
Write-Output "Saved $character/$name.uasset"
