param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../../..").Path
$relative='Content/WorldGeneration/VillageTavern/DiningBowls'
$live=Join-Path $project $relative
$stage=Join-Path "$project/Saved/TavernDiningBowls" ([guid]::NewGuid().ToString('N'))
$service='Content/WorldGeneration/VillageTavern/Service'
$original=@{}
if(Test-Path -LiteralPath $live){
    foreach($file in Get-ChildItem -LiteralPath $live -File){
        $original[$file.Name]=(Get-FileHash -LiteralPath $file.FullName).Hash
    }
}
New-Item -ItemType Directory -Path "$stage/$service","$stage/Config" -Force | Out-Null
$hostFile="$stage/DiningBowls.uproject"
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
    @{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $hostFile -Encoding utf8
@('[ConsoleVariables]','Interchange.FeatureFlags.Import.FBX=0') | Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding utf8
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    foreach($pattern in 'T_Kiln*','M_TavernStoneware.*','MI_TavernClay.*','MI_TavernHoneyGlaze.*','MI_TavernAshGlaze.*'){
        Get-ChildItem -LiteralPath "$project/$service" -Filter $pattern -File | Copy-Item -Destination "$stage/$service"
    }
    $exe="$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
    & $exe $hostFile /Engine/Maps/Entry -run=pythonscript "-script=$PSScriptRoot/import_bowls.py" -unattended -nop4 -nosound -NullRHI -nosplash -Multiprocess -NoAssetRegistryCacheWrite -ddc=InstalledNoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$stage/import.log" *> "$stage/console.log"
    if($LASTEXITCODE -or !(Test-Path -LiteralPath "$stage/saved.json")){throw "Dining bowl import failed in $stage/import.log"}
    $outputs=foreach($name in Get-Content -LiteralPath "$stage/saved.json" -Raw | ConvertFrom-Json){
        Get-Item -LiteralPath "$stage/$relative/$name.uasset"
        Get-ChildItem -LiteralPath "$stage/$relative" -File | Where-Object {$_.BaseName -ceq $name -and $_.Extension -in '.uexp','.ubulk','.uptnl'}
    }
    foreach($file in $outputs){
        $target=Join-Path $live $file.Name
        $current=if(Test-Path -LiteralPath $target){(Get-FileHash -LiteralPath $target).Hash}
        if($current -ne $original[$file.Name]){throw "Concurrent change to $target"}
    }
    if($original.Count -and (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match '(?i)FPSGAME(?:\.uproject|[" ]|$)'})){
        $guard="$stage/loaded_bowls.py"
        @"
import json, pathlib, unreal
if pathlib.Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()!=pathlib.Path(r'$project').resolve():
    raise RuntimeError('Different active project')
for name in json.loads(pathlib.Path(r'$stage/saved.json').read_text()):
    if unreal.find_object(None,'/Game/WorldGeneration/VillageTavern/DiningBowls/'+name+'.'+name):
        raise RuntimeError('Dining bowl package already loaded in editor: '+name)
"@ | Set-Content -LiteralPath $guard -Encoding UTF8
        & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $guard
        if($LASTEXITCODE){throw "Loaded package guard failed"}
    }
    New-Item -ItemType Directory -Path $live -Force | Out-Null
    foreach($file in $outputs){
        $target=Join-Path $live $file.Name
        $temp=$target+'.'+[guid]::NewGuid().ToString('N')+'.tmp'
        [IO.File]::Copy($file.FullName,$temp,$false)
        if([IO.File]::Exists($target)){[IO.File]::Replace($temp,$target,[NullString]::Value)}
        else{[IO.File]::Move($temp,$target)}
    }
    Copy-Item -LiteralPath "$stage/saved.json" -Destination "$project/SourceAssets/HillsVillageTavern/DiningBowls/saved.json" -Force
    Write-Output "Saved $($outputs.Count) dining bowl packages."
}finally{
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
