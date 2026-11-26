param([string]$Work='F:/FPSGAMEData/ArtProduction/VillageMasonry',[string]$GateSource='')
$ErrorActionPreference='Stop'
$project=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$run=Join-Path $Work (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$content=Join-Path $run 'Content'
$hills='WorldGeneration/TemperateHills'
New-Item -ItemType Directory -Path "$content/$hills","$run/Config" -Force | Out-Null
foreach($entry in 'UnrealNormandy',"$hills/OldChapel","$hills/VillageDefenses","$hills/VillagePerimeter","$hills/HighVillageDefense","$hills/EcologyUpgrade"){
    New-Item -ItemType Junction -Path "$content/$entry" -Target "$project/Content/$entry" | Out-Null
}
foreach($gate in ($GateSource -split ';' | Where-Object {$_})){
    $gateFolder=Split-Path ($gate.Replace('/Game/','')) -Parent
    if(!(Test-Path "$content/$gateFolder")){
        New-Item -ItemType Junction -Path "$content/$gateFolder" -Target "$project/Content/$gateFolder" | Out-Null
    }
}
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(@{Name='GeometryScripting';Enabled=$true},@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} |
    ConvertTo-Json -Depth 4 | Set-Content "$run/Masonry.uproject" -Encoding utf8
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') | Set-Content "$run/Config/DefaultEngine.ini" -Encoding utf8
$env:VILLAGE_MASONRY_WORK=$run
$env:VILLAGE_MASONRY_GATE=$GateSource
$cmd='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$argsList=@(('"'+$run+'/Masonry.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="'+$PSScriptRoot+'/author_masonry.py"'),
    '-NullRHI','-unattended','-nosplash','-nosound','-nop4','-Multiprocess','-NoAssetRegistryCacheWrite',
    '-ini:Engine:[SystemSettings]:Editor.AsyncStaticMeshCompilation=0',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncStaticMeshCompilation=False',
    '-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',
    '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',
    ('-abslog="'+$run+'/author.log"'))
$proc=Start-Process -FilePath $cmd -ArgumentList $argsList -Wait -PassThru -WindowStyle Hidden
if($proc.ExitCode -ne 0 -or !(Test-Path "$run/saved.json")){
    Select-String "$run/author.log" -Pattern 'LogPython: Error|Fatal error' | Select-Object -Last 10
    throw "Masonry authoring failed. $run"
}
$receipt=Get-Content "$run/saved.json" -Raw | ConvertFrom-Json
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
try {
    try{$null=$mutex.WaitOne()}catch [Threading.AbandonedMutexException]{}
    foreach($row in $receipt.meshes){
        $rel=$row.asset.Substring(6)+'.uasset'
        $destination=Join-Path "$project/Content" $rel
        New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
        $source=Join-Path $content $rel
        if(Test-Path $destination){
            if((Get-FileHash $source).Hash -eq (Get-FileHash $destination).Hash){continue}
            throw "Existing masonry package differs at $destination. Publish through its owning editor."
        }
        $stage="$destination.$PID.tmp"
        Copy-Item -LiteralPath $source -Destination $stage
        [IO.File]::Move($stage,$destination)
    }
} finally {$mutex.ReleaseMutex();$mutex.Dispose()}
Copy-Item -LiteralPath "$run/saved.json" -Destination "$run/published.json"
Write-Output "Published masonry packages: $run/published.json"
