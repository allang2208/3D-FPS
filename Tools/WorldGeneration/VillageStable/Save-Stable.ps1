param(
    [ValidateSet('Assets','Level','Perimeter','GroundDetail','Horses','Riding','Publish')][string]$Phase='Assets',
    [string]$Batch='F:/FPSGAMEData/ArtProduction/HillsVillageStable/AssemblyR1-20261122',
    [string]$Engine='E:/Program Files (x86)/UE_5.8'
)
$ErrorActionPreference='Stop'
$project=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
if($Phase -eq 'Perimeter' -and !$PSBoundParameters.ContainsKey('Batch')){
    $Batch='F:/FPSGAMEData/ArtProduction/HillsVillageStable/OpenYardR6-20261123'
}
if($Phase -eq 'GroundDetail' -and !$PSBoundParameters.ContainsKey('Batch')){
    $Batch='F:/FPSGAMEData/ArtProduction/HillsVillageStable/GroundDetailR4-20261122'
}
if($Phase -eq 'Horses' -and !$PSBoundParameters.ContainsKey('Batch')){
    $Batch='F:/FPSGAMEData/ArtProduction/HillsVillageStable/StableHorsesR7b-20261123'
}
$run=Join-Path $Batch 'Author'
if($Phase -eq 'Riding' -and !$PSBoundParameters.ContainsKey('Batch')){
    $run='F:/FPSGAMEData/ArtProduction/HillsVillageStable/RidingR8-20261123/Author'
}
$stage=Join-Path $run 'Host'
$content=@((Get-Item -LiteralPath "$project/Content").Target)[0]
$level='WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap'
$kit='WorldGeneration/TemperateHills/VillageStable'
$env:STABLE_RUN=$run
$env:STABLE_PHASE=$Phase
$env:STABLE_PROJECT=$project
$env:UE_SKIP_UBT_SDK_SETUP='1'
$cache='F:/FPSGAMEData/Caches/DerivedDataCache'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!(Test-Path -LiteralPath "$stage/FPSGAME.uproject")){
        . (Join-Path $PSScriptRoot '../VillageCarpenter/YardDetail/stage_host.ps1')
        $privatePackages=if($Phase -eq 'Riding'){@($level)}else{@($level,$kit)}
        $null=New-YardAuthorHost $project $run $content @($privatePackages)
        $hashes=@{}
        if($Phase -ne 'Riding' -and (Test-Path -LiteralPath "$content/$kit")){
            foreach($item in Get-ChildItem -LiteralPath "$content/$kit" -Recurse -File){
                $rel=[IO.Path]::GetRelativePath($content,$item.FullName).Replace('\','/')
                $hashes[$rel]=(Get-FileHash -LiteralPath $item.FullName).Hash.ToLowerInvariant()
            }
        }
        ConvertTo-Json -InputObject $hashes | Set-Content -LiteralPath "$run/previous-kit.json" -Encoding utf8NoBOM
    }
    if($Phase -in 'Level','Perimeter','GroundDetail','Horses','Riding'){
        if($Phase -eq 'Level' -and !(Test-Path -LiteralPath "$run/imported.json")){throw 'Stable kit is still being authored'}
        # Read the project's discovery snapshot from a private copy. The staged host
        # has its own Intermediate and scans newly generated stable assets on load.
        $intermediate=Join-Path $stage 'Intermediate'
        foreach($entry in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin'){
            $cached=Join-Path "$project/Intermediate" $entry
            $dest=Join-Path $intermediate $entry
            if(Test-Path -LiteralPath $cached){
                try {
                    if((Get-Item -LiteralPath $cached).PSIsContainer){
                        [IO.Directory]::CreateDirectory($dest) | Out-Null
                        foreach($f in Get-ChildItem -LiteralPath $cached -File){
                            Copy-Item -Force -LiteralPath $f.FullName -Destination $dest
                        }
                    } else {Copy-Item -Force -LiteralPath $cached -Destination $dest}
                } catch {Write-Verbose "UE will discover assets from disk for $entry."}
            }
        }
        $stamp=(Get-Date -Format 'yyyyMMdd-HHmmss-fff')
        $backup=Join-Path $run "Before/$stamp/L_AbandonedVillage.umap"
        New-Item -ItemType Directory -Force -Path (Split-Path $backup) | Out-Null
        Copy-Item -LiteralPath "$content/$level" -Destination $backup
        Copy-Item -Force -LiteralPath $backup -Destination "$stage/Content/$level"
        $env:STABLE_PREVIOUS=$backup
        $moduleList="$project/Binaries/Win64/UnrealEditor.modules"
        Copy-Item -Force -LiteralPath $moduleList -Destination "$stage/Binaries/Win64"
        foreach($mod in (Get-Content -Raw $moduleList | ConvertFrom-Json).Modules.PSObject.Properties){
            Copy-Item -Force -LiteralPath "$project/Binaries/Win64/$($mod.Value)" -Destination "$stage/Binaries/Win64"
        }
    }
    if($Phase -ne 'Publish'){
        $jobs=if($Phase -eq 'Horses'){@('HorseAssets','Horses')}else{@($Phase)}
        foreach($jobName in $jobs){
            $script=switch($jobName){
                'Assets' {'import_stable.py'}
                'HorseAssets' {'Horses/save_horse_assets.py'}
                default {'save_level.py'}
            }
            $receipt=switch($jobName){
                'Assets' {'imported.json'}
                'HorseAssets' {'horse-assets.json'}
                default {'level-saved.json'}
            }
            $log=Join-Path $run "$jobName-engine.log"
            $started=Get-Date
            $opts=@(('"'+$stage+'/FPSGAME.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
                ('-script="'+$PSScriptRoot+'/'+$script+'"'),'-unattended','-NullRHI','-nosplash','-nosound','-nop4',
                '-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
                '-ini:Engine:[ConsoleVariables]:Interchange.FeatureFlags.Import.FBX=False',
                ('-LocalDataCachePath='+$cache),('-ZenDataPath='+$cache+'/Zen'),
                ('-ini:Engine:[VirtualTextureChunkDDCCache]:Path='+$cache+'/VT'),('-abslog="'+$log+'"'),
                '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
                '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
            if($Phase -in 'Perimeter','GroundDetail','Horses','Riding'){$opts+='-asyncStaticMeshCompilation=0'}
            if($jobName -eq 'HorseAssets'){
                $opts=@($opts | Where-Object {$_ -ne '-NullRHI'})
                $opts+=@('-AllowCommandletRendering','-d3d12','-sm6','-RenderOffscreen','-asyncSkeletalMeshCompilation=0')
            }
            $process=Start-Process -WindowStyle Hidden -PassThru -Wait -FilePath "$Engine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" -ArgumentList $opts
            if($process.ExitCode -ne 0 -or !(Test-Path -LiteralPath "$run/$receipt") -or (Get-Item "$run/$receipt").LastWriteTime -lt $started){
                Get-Content -LiteralPath $log -Tail 32
                throw "Stable $jobName did not finish. $log"
            }
        }
    }
    if($Phase -ne 'Assets'){
        $projectFile=[IO.Path]::GetFullPath((Join-Path $project 'FPSGAME.uproject'))
        $useBridge=[bool]@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {
            $match=[regex]::Match([string]$_.CommandLine,'(?i)(?:"([^"]+\.uproject)"|(?:^|\s)([^\s"]+\.uproject))(?=\s|$)')
            $candidate=($match.Groups[1].Value+$match.Groups[2].Value)
            !$match.Success -or ![IO.Path]::IsPathFullyQualified($candidate) -or [IO.Path]::GetFullPath($candidate) -eq $projectFile
        })
        if(!$useBridge){
            & python "$PSScriptRoot/publish.py"
            if($LASTEXITCODE -ne 0){throw 'Stable publication deferred.'}
        }
    }
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
if($Phase -ne 'Assets' -and $useBridge){
    $bridge=Join-Path $run 'publish-loaded.py'
    @"
import os, runpy
os.environ.update(STABLE_RUN=r'$run',STABLE_PROJECT=r'$project')
runpy.run_path(r'$PSScriptRoot/publish.py',run_name='__main__')
"@ | Set-Content -LiteralPath $bridge -Encoding utf8NoBOM
    $bridgeReceipt=Join-Path $run ('bridge-'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'.json')
    & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $bridge -OutputFile $bridgeReceipt -MaxOutputChars 1500 -QueueWaitSeconds 300
    if($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath "$run/published.json")){throw 'Stable publication deferred by active editor.'}
}
