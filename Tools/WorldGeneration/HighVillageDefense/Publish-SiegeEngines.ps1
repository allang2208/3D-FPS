param([Parameter(Mandatory)][string]$Run)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path "$PSScriptRoot/../../..").Path
$env:VILLAGE_SIEGE_RUN = $Run
$env:HIGH_VILLAGE_PROJECT = $project
$rel = 'Content/WorldGeneration/TemperateHills/HighVillageDefense/SiegeEngines'
$live = Join-Path $project $rel
$session = Join-Path $Run ('Import-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$env:VILLAGE_SIEGE_STAGE = $session
$stage = Join-Path $session $rel
New-Item -ItemType Directory -Force -Path $stage,"$session/Config" | Out-Null
$before = @{}
if(Test-Path -LiteralPath $live){
    foreach($asset in Get-ChildItem -LiteralPath $live -File){$before[$asset.Name]=(Get-FileHash $asset.FullName).Hash}
}
# The import project mounts only the three material donor directories and owns every writable siege package.
foreach ($branch in @('WorldGeneration/TemperateHills/OldChapel','WorldGeneration/TemperateHills/VillageBlacksmith','Props','Building/GunWorkbenchMedieval20260928')){
    $link=Join-Path "$session/Content" $branch
    New-Item -ItemType Directory -Force -Path (Split-Path $link) | Out-Null
    if(!(Test-Path -LiteralPath $link)){New-Item -ItemType Junction -Path $link -Target (Join-Path "$project/Content" $branch) | Out-Null}
}
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(@{Name='GeometryScripting';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true},@{Name='PythonScriptPlugin';Enabled=$true})} | ConvertTo-Json -Depth 4 | Set-Content "$session/SiegeKit.uproject" -Encoding utf8
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') | Set-Content "$session/Config/DefaultEngine.ini"
$editor='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$argsList=@(('"'+$session+'/SiegeKit.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="'+$PSScriptRoot+'/import_siege_meshes.py"'),'-NullRHI','-nosound','-nop4','-unattended','-Multiprocess','-ini:Engine:[ConsoleVariables]:Interchange.FeatureFlags.Import.FBX=0','-NoAssetRegistryCacheWrite','-AssetGatherAll=false','-ini:Engine:[SystemSettings]:Editor.AsyncStaticMeshCompilation=0','-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncStaticMeshCompilation=False','-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',('-abslog="'+$session+'/author.log"'))
$proc=Start-Process -FilePath $editor -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
if($proc.ExitCode -ne 0 -or !(Test-Path "$session/saved.json")){throw "Siege import failed. See $session/author.log"}
$guard=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    try{$held=$guard.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    foreach($asset in Get-ChildItem -LiteralPath $stage -File -Filter '*.uasset'){
        $dest=Join-Path $live $asset.Name
        if((Test-Path $dest) -ne $before.ContainsKey($asset.Name) -or ((Test-Path $dest) -and (Get-FileHash $dest).Hash -ne $before[$asset.Name])){throw "Concurrent asset change $dest"}
    }
    if(!(Test-Path $live)){
        $pending="$live.$PID.pending"
        Copy-Item -LiteralPath $stage -Destination $pending -Recurse
        [IO.Directory]::Move($pending,$live)
    }else{
        New-Item -ItemType Directory -Force -Path "$session/Before" | Out-Null
        foreach($asset in Get-ChildItem -LiteralPath $stage -File -Filter '*.uasset'){
            $dest=Join-Path $live $asset.Name
            Copy-Item -LiteralPath $asset.FullName -Destination "$dest.$PID.pending"
            if(Test-Path $dest){[IO.File]::Replace("$dest.$PID.pending",$dest,"$session/Before/$($asset.Name)")}else{[IO.File]::Move("$dest.$PID.pending",$dest)}
        }
    }
    $recovery=Join-Path $Run $rel
    New-Item -ItemType Directory -Force -Path $recovery | Out-Null
    foreach($asset in Get-ChildItem -LiteralPath $stage -File -Filter '*.uasset'){
        Copy-Item -LiteralPath $asset.FullName -Destination (Join-Path $recovery $asset.Name) -Force
    }
    Copy-Item -LiteralPath "$session/saved.json" -Destination "$Run/published.json"
}finally{if($held){$guard.ReleaseMutex()};$guard.Dispose()}
