param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../../..").Path
$relative='Content/WorldGeneration/VillageTavern/DryingRack'
$live=Join-Path $project $relative
$stage=Join-Path "$project/Saved/TavernDryingRack" ([guid]::NewGuid().ToString('N'))
$savedAtStart=@{}
if(Test-Path -LiteralPath $live){
    foreach($file in Get-ChildItem -LiteralPath $live -File){$savedAtStart[$file.Name]=(Get-FileHash -LiteralPath $file.FullName).Hash}
}
New-Item -ItemType Directory -Path "$stage/Content","$stage/Config" -Force|Out-Null
$hostfile="$stage/DryingRail.uproject"
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
    @{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})}|
    ConvertTo-Json -Depth 4|Set-Content -LiteralPath $hostfile -Encoding utf8
@('[ConsoleVariables]','Interchange.FeatureFlags.Import.FBX=0')|Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding utf8
$exe="$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
& $exe $hostfile /Engine/Maps/Entry -run=pythonscript "-script=$PSScriptRoot/import_rack.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -NoAssetRegistryCacheWrite -ddc=InstalledNoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$stage/import.log" *> "$stage/console.log"
if($LASTEXITCODE -or !(Test-Path -LiteralPath "$stage/saved.json")){throw "Drying rail import failed. See $stage/import.log"}
$outputs=foreach($name in Get-Content -LiteralPath "$stage/saved.json" -Raw|ConvertFrom-Json){
    Get-Item -LiteralPath "$stage/$relative/$name.uasset"
    Get-ChildItem -LiteralPath "$stage/$relative" -File|Where-Object {$_.BaseName -eq $name -and $_.Extension -in '.uexp','.ubulk','.uptnl'}
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
    New-Item -ItemType Directory -Path $live -Force|Out-Null
    foreach($file in $outputs){[IO.File]::Copy($file.FullName,(Join-Path $live $file.Name),$true)}
    Copy-Item -LiteralPath "$stage/saved.json" -Destination "$project/SourceAssets/HillsVillageTavern/DryingRack/saved.json" -Force
    Write-Output "Published $($outputs.Count) drying rail packages."
}finally{
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
