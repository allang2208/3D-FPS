param([string]$EngineRoot = 'E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$relative = 'Content/WorldGeneration/VillageTavern/EatingUtensils'
$live = Join-Path $root $relative
$stage = Join-Path "$root/Saved/TavernEatingUtensils" ([Guid]::NewGuid().ToString('N'))
$original = @{}
if (Test-Path -LiteralPath $live) {
    Get-ChildItem -LiteralPath $live -File | ForEach-Object {
        $original[$_.Name] = (Get-FileHash -LiteralPath $_.FullName).Hash
    }
}
New-Item -ItemType Directory -Force "$stage/Content","$stage/Config" | Out-Null
$project = "$stage/EatingUtensils.uproject"
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
    @{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true}
)} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $project -Encoding utf8
'[ConsoleVariables]','Interchange.FeatureFlags.Import.FBX=0' |
    Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding utf8
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    $exe = Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    & $exe $project /Engine/Maps/Entry -run=pythonscript "-script=$PSScriptRoot/import_utensils.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -AssetGatherAll=false -NoAssetRegistryCacheWrite -ddc=InstalledNoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' "-abslog=$stage/import.log" *> "$stage/console.log"
    if ($LASTEXITCODE -or !(Test-Path -LiteralPath "$stage/saved.json")) {
        throw "Eating utensil import failed. See $stage/import.log"
    }
    $names = Get-Content -LiteralPath "$stage/saved.json" -Raw | ConvertFrom-Json
    $files = foreach ($name in $names) {
        Get-Item -LiteralPath "$stage/$relative/$name.uasset"
        Get-ChildItem -LiteralPath "$stage/$relative" -File |
            Where-Object {$_.BaseName -eq $name -and $_.Extension -in '.ubulk','.uexp','.uptnl'}
    }
    foreach ($file in $files) {
        $target = Join-Path $live $file.Name
        $hash = if (Test-Path -LiteralPath $target) { (Get-FileHash -LiteralPath $target).Hash }
        if ($hash -ne $original[$file.Name]) { throw "A target package changed during import: $target" }
    }
    if ($original.Count -and (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" |
            Where-Object {$_.CommandLine -match '(?i)FPSGAME(\.uproject|[" ]|$)'})) {
        $guard = "$stage/loaded.py"
        @'
import json, pathlib, unreal
for name in json.loads((pathlib.Path(__file__).parent/'saved.json').read_text()):
    path = '/Game/WorldGeneration/VillageTavern/EatingUtensils/'+name+'.'+name
    if unreal.find_object(None, path):
        raise RuntimeError('The open project holds '+path)
'@ | Set-Content -LiteralPath $guard -Encoding utf8
        & "$root/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $guard
        if ($LASTEXITCODE) { throw 'The open editor holds an eating utensil package.' }
    }
    New-Item -ItemType Directory -Force $live | Out-Null
    foreach ($file in $files) {
        $target = Join-Path $live $file.Name
        $next = $target+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
        [IO.File]::Copy($file.FullName,$next,$false)
        if ([IO.File]::Exists($target)) { [IO.File]::Replace($next,$target,[NullString]::Value) }
        else { [IO.File]::Move($next,$target) }
    }
    Copy-Item -LiteralPath "$stage/saved.json" -Destination "$root/SourceAssets/HillsVillageTavern/EatingUtensils/saved.json" -Force
    Write-Output ("Published "+($names -join ', ')+" to "+$live)
} finally {
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
