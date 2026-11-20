$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$relative = 'Characters/VillageTavernKeeper'
$source = Join-Path "$project/Content" $relative
$published = Join-Path $source 'A_TavernKeeper_Idle.uasset'
$work = Join-Path $project ("Saved/TavernKeeperIdleAuthoring/" + [Guid]::NewGuid().ToString('N'))
$content = Join-Path "$work/Content" $relative
$descriptor = Join-Path $work 'TavernKeeperIdle.uproject'
New-Item -ItemType Directory -Path $content -Force | Out-Null
@{
    FileVersion=3
    EngineAssociation='5.8'
    Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})
} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $descriptor -Encoding ascii

$staged = Join-Path $project "Saved/TavernKeeperMeshAuthoring/Host/Content/$relative"
$inputs = $source
# Work from the character author's saved packages while publication is queued.
while (!(Test-Path -LiteralPath "$source/SK_TavernKeeper_Skeleton.uasset")) {
    if ((Test-Path -LiteralPath "$project/SourceAssets/VillageTavernKeeper/FullBody/UEAuthoringR1/character_saved.json") -and
        (Test-Path -LiteralPath "$staged/SK_TavernKeeper_Skeleton.uasset")) {
        $inputs = $staged
        break
    }
    Start-Sleep -Seconds 5
}
foreach ($dep in @('SK_TavernKeeper.uasset','SK_TavernKeeper_Skeleton.uasset','Materials','Textures')) {
    Copy-Item -LiteralPath (Join-Path $inputs $dep) -Destination $content -Recurse
}
$env:TAVERN_IDLE_PYTHON = (Get-Command python.exe -CommandType Application | Select-Object -First 1).Source
$env:TAVERN_IDLE_WORK = $work
$env:UE_SKIP_UBT_SDK_SETUP = '1'
$commandlet = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
& $commandlet $descriptor -run=pythonscript "-script=$PSScriptRoot/save_idle.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -asyncskinnedassetcompilation=0 -asynctexturecompilation=0 '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$work/engine.log" *> "$work/console.log"
if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath "$work/saved.json")) {
    throw "Animation authoring failed, see $work/engine.log"
}
# The mesh publisher installs the skeleton last. Match the snapshot we animated.
while (!(Test-Path -LiteralPath "$source/SK_TavernKeeper_Skeleton.uasset")) {
    Start-Sleep -Seconds 5
}
if ((Get-FileHash -LiteralPath "$source/SK_TavernKeeper_Skeleton.uasset").Hash -ne
    (Get-FileHash -LiteralPath "$content/SK_TavernKeeper_Skeleton.uasset").Hash) {
    throw 'The published skeleton changed during authoring. Rebuild the idle against it.'
}
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    $temporary = "$published.idle-$PID.tmp"
    [IO.File]::Copy("$content/A_TavernKeeper_Idle.uasset", $temporary)
    [IO.File]::Move($temporary, $published)
} finally {
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
Write-Output "Saved $published"
