$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$source = Join-Path $project 'SourceAssets/VillageHerbalist/FullBody/WalkR1'
$relative = 'Characters/VillageHerbalist'
$character = Join-Path "$project/Content" $relative
$work = Join-Path $project ('Saved/VillageHerbalistWalk/' + [Guid]::NewGuid().ToString('N'))
$staging = Join-Path "$work/Content" $relative
$descriptor = Join-Path $work 'HerbalistWalk.uproject'
$filename = 'A_VillageHerbalist_Walk.uasset'
$published = Join-Path $character $filename
$commandlet = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
New-Item -ItemType Directory -Path $source,$staging -Force | Out-Null
@{
    FileVersion=3
    EngineAssociation='5.8'
    Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $descriptor -Encoding ascii
foreach ($dependency in @('SK_VillageHerbalist.uasset','SK_VillageHerbalist_Skeleton.uasset','Materials','Textures')) {
    Copy-Item -Recurse -LiteralPath (Join-Path $character $dependency) -Destination $staging
}
& python.exe -I "$PSScriptRoot/author_walk.py" "$source/motion.json"
if ($LASTEXITCODE -ne 0) { throw 'Could not fit the walk to the herbalist' }
$env:HERBALIST_WALK_RECEIPT = "$work/saved.json"
$env:UE_SKIP_UBT_SDK_SETUP = '1'
& $commandlet $descriptor -run=pythonscript "-script=$PSScriptRoot/save_walk.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -asyncskinnedassetcompilation=0 -asynctexturecompilation=0 '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$work/engine.log" *> "$work/console.log"
if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $env:HERBALIST_WALK_RECEIPT)) {
    throw "Background asset save failed. See $work/engine.log"
}
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    $skeletonName = 'SK_VillageHerbalist_Skeleton.uasset'
    if ((Get-FileHash -LiteralPath "$character/$skeletonName").Hash -ne (Get-FileHash -LiteralPath "$staging/$skeletonName").Hash) {
        throw 'The installed skeleton changed during authoring'
    }
    $receipt = Get-Content -Raw -LiteralPath $env:HERBALIST_WALK_RECEIPT | ConvertFrom-Json
    $receipt | Add-Member -MemberType NoteProperty -Name 'sha256' -Value (Get-FileHash -LiteralPath "$staging/$filename").Hash
    $temporary = "$published.walk-$PID.tmp"
    if (Test-Path -LiteralPath $published) {
        $old = Get-Content -Raw -LiteralPath "$source/installed.json" | ConvertFrom-Json
        if ($old.sha256 -ne (Get-FileHash -LiteralPath $published).Hash) {
            throw "Another walk asset already occupies $published"
        }
        [IO.File]::Copy("$staging/$filename", $temporary)
        [IO.File]::Replace($temporary, $published, "$work/previous-walk.uasset")
    } else {
        [IO.File]::Copy("$staging/$filename", $temporary)
        [IO.File]::Move($temporary, $published)
    }
    $receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$source/installed.json" -Encoding utf8
} finally {
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
Write-Output "Installed $published ($($receipt.frames) frames, $($receipt.speed_cm_s) cm/s)."
