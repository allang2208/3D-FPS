param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8', [switch]$WeaponDisplays, [switch]$ForgeWeaponDisplay, [switch]$WorkshopLayout, [switch]$Herbalist, [switch]$CeilingLantern)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$logDirectory=if($Herbalist){Join-Path $project 'Saved/VillageHerbalist/Publish'}else{Join-Path $project 'Saved/VillageCarpenter/Publish'}
New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
$batchMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$batchMutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held=$true }
    $openProjectEditor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" |
        Where-Object { $_.CommandLine -like '*FPSGAME.uproject*' -or -not $_.CommandLine }
    if($openProjectEditor){throw 'Use the current editor batch bridge to save the village.'}
    # Use private binaries and Saved paths; the production Content mount is the
    # only destination of the map and texture saves.
    $authorProject=Join-Path $logDirectory 'Host'
    $authorBinaries=Join-Path $authorProject 'Binaries/Win64'
    New-Item -ItemType Directory -Force -Path $authorBinaries | Out-Null
    Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$authorProject/FPSGAME.uproject" -Force
    if(-not(Test-Path -LiteralPath "$authorProject/Config")){
        Copy-Item -LiteralPath "$project/Config" -Destination "$authorProject/Config" -Recurse
    }
    foreach($name in 'Content','Plugins','Shaders'){
        if(-not(Test-Path -LiteralPath "$authorProject/$name")){
            New-Item -ItemType Junction -Path "$authorProject/$name" -Target "$project/$name" | Out-Null
        }
    }
    foreach($name in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules'){
        Copy-Item -LiteralPath "$project/Binaries/Win64/$name" -Destination "$authorBinaries/$name" -Force
    }
    $stage=Get-Date -Format 'yyyyMMdd-HHmmss'
    $log=Join-Path $logDirectory "$stage-engine.log"
    $scriptPath=if($Herbalist){Join-Path $project 'Tools/WorldGeneration/VillageHerbalist/publish.py'}elseif($ForgeWeaponDisplay){Join-Path $project 'Tools/WorldGeneration/VillageBlacksmith/save_weapon_display.py'}elseif($CeilingLantern){Join-Path $PSScriptRoot 'save_ceiling_lantern.py'}else{Join-Path $PSScriptRoot 'publish.py'}
    $arguments=@(('"'+$authorProject+'/FPSGAME.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
        ('-script="'+$scriptPath+'"'),'-unattended','-nop4','-nosplash','-nosound','-NullRHI',
        '-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',('-abslog="'+$log+'"'),
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    if($WeaponDisplays){$arguments+='-VillageWeaponDisplays'}
    if($WorkshopLayout){$arguments+='-VillageWorkshopLayout'}
    $exe=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $oldSkip=$env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $process=Start-Process -FilePath $exe -ArgumentList $arguments -WindowStyle Hidden -PassThru
        $null=$process.Handle
        $process.WaitForExit()
        $process.Refresh()
    } finally { $env:UE_SKIP_UBT_SDK_SETUP=$oldSkip }
    Get-Content -LiteralPath $log -Tail 15
    if($process.ExitCode -ne 0){throw "Village commandlet exited with $($process.ExitCode). $log"}
} finally {
    if($held){$batchMutex.ReleaseMutex()}
    $batchMutex.Dispose()
}
