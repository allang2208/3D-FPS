param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../../..").Path
$relative='Content/WorldGeneration/VillageTavern/KitchenHearth'
$live=Join-Path $project $relative
$stage=Join-Path "$project/Saved/TavernKitchenHearth" ([guid]::NewGuid().ToString('N'))
$savedAtStart=@{}
if(Test-Path -LiteralPath $live){
    foreach($file in Get-ChildItem -LiteralPath $live -File){$savedAtStart[$file.Name]=(Get-FileHash -LiteralPath $file.FullName).Hash}
}
New-Item -ItemType Directory -Path "$stage/Content","$stage/Config" -Force | Out-Null
$hostFile="$stage/TavernKitchenHearth.uproject"
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
    @{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $hostFile -Encoding utf8
@('[ConsoleVariables]','Interchange.FeatureFlags.Import.FBX=0') | Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding utf8
& python "$PSScriptRoot/stage.py" $project $stage
if($LASTEXITCODE){throw "Supplier staging failed in $stage"}
$exe="$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
& $exe $hostFile /Engine/Maps/Entry -run=pythonscript "-script=$PSScriptRoot/import_hearth.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -NoAssetRegistryCacheWrite -ddc=InstalledNoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$stage/import.log" *> "$stage/console.log"
if($LASTEXITCODE -or !(Test-Path -LiteralPath "$stage/saved.json")){throw "Cook hearth import failed in $stage"}
$outputs=foreach($name in Get-Content -LiteralPath "$stage/saved.json" -Raw | ConvertFrom-Json){
    Get-Item -LiteralPath "$stage/$relative/$name.uasset"
    Get-ChildItem -LiteralPath "$stage/$relative" -File | Where-Object {$_.BaseName -eq $name -and $_.Extension -in '.uexp','.ubulk','.uptnl'}
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    foreach($file in $outputs){
        $target=Join-Path $live $file.Name
        if(Test-Path -LiteralPath $target){
            if(!$savedAtStart.ContainsKey($file.Name) -or $savedAtStart[$file.Name] -ne (Get-FileHash -LiteralPath $target).Hash){throw "Concurrent change at $target"}
        }elseif($savedAtStart.ContainsKey($file.Name)){throw "Concurrent removal at $target"}
    }
    $publishedBefore=@($outputs | Where-Object {$savedAtStart.ContainsKey($_.Name)})
    $editor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match '(?i)FPSGAME(?:\.uproject|[" ]|$)'}
    if($publishedBefore.Count -and $editor){
        $guard="$stage/loaded_hearth.py"
        @"
import unreal
from pathlib import Path
import json
if Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()!=Path(r'$project').resolve():
    raise RuntimeError('Connected editor is using a different project')
for name in json.loads(Path(r'$stage/saved.json').read_text()):
    if unreal.find_object(None, '/Game/WorldGeneration/VillageTavern/KitchenHearth/'+name+'.'+name):
        raise RuntimeError('Loaded cook hearth asset '+name)
"@ | Set-Content -LiteralPath $guard -Encoding UTF8
        & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $guard
        if($LASTEXITCODE){throw "Active editor has loaded cook hearth packages"}
    }
    New-Item -ItemType Directory -Path $live -Force | Out-Null
    foreach($file in $outputs){[IO.File]::Copy($file.FullName,(Join-Path $live $file.Name),$true)}
    Copy-Item -LiteralPath "$stage/saved.json" -Destination "$project/SourceAssets/HillsVillageTavern/KitchenHearth/saved.json" -Force
    Write-Output "Published $($outputs.Count) cook hearth packages."
}finally{
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
