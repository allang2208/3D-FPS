param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$stage=Join-Path "$root/Saved/TavernTableGame" ([Guid]::NewGuid().ToString('N'))
$relative='WorldGeneration/VillageTavern/TableGame'
$target="$root/Content/$relative"
$inputs=@{}
if(Test-Path -LiteralPath $target) {
    Get-ChildItem -LiteralPath $target -File | ForEach-Object {$inputs[$_.Name]=(Get-FileHash $_.FullName).Hash}
}
New-Item -ItemType Directory -Force "$stage/Config","$stage/Content" | Out-Null
$project="$stage/TavernTables.uproject"
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
    @{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true}
)}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $project -Encoding utf8
'[ConsoleVariables]','Interchange.FeatureFlags.Import.FBX=0'|Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding utf8
$log="$stage/import.log"
$exe="$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
& $exe $project /Engine/Maps/Entry -run=pythonscript "-script=$PSScriptRoot/import_tables.py" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -AssetGatherAll=false -NoAssetRegistryCacheWrite -ddc=InstalledNoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$log" *> "$stage/console.log"
if($LASTEXITCODE -or !(Test-Path -LiteralPath "$stage/saved.json")){throw "Table game import failed. See $log"}
$names=Get-Content "$stage/saved.json" -Raw|ConvertFrom-Json
$files=foreach($name in $names){
    Get-Item -LiteralPath "$stage/Content/$relative/$name.uasset"
    Get-ChildItem -LiteralPath "$stage/Content/$relative" -File | Where-Object {$_.BaseName -eq $name -and $_.Extension -in '.ubulk','.uexp','.uptnl'}
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    New-Item -ItemType Directory -Force $target | Out-Null
    foreach($file in $files){
        $live=Join-Path $target $file.Name
        if(Test-Path -LiteralPath $live){
            if(!$inputs.ContainsKey($file.Name) -or (Get-FileHash $live).Hash -ne $inputs[$file.Name]){
                throw "A concurrently edited asset is already present: $live"
            }
        } elseif($inputs.ContainsKey($file.Name)){throw "An existing package was moved during import: $live"}
    }
    foreach($file in $files){[IO.File]::Copy($file.FullName,(Join-Path $target $file.Name),$true)}
    Write-Output ("Saved "+($names -join ', ')+" to "+$target)
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
