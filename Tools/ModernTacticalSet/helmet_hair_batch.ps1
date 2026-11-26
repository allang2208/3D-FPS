param([ValidateSet('HairEnvelope','SourceHead','Rendering','Save')][string]$Stage='HairEnvelope')
$ErrorActionPreference='Stop'
$hairRoot='D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/HelmetHairFitR1'
$hairRun=Get-Date -Format 'yyyyMMdd-HHmmss'
$hairGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$hairHeld=$false
try {
    # Read stages use their own content-only host, never write packages, never
    # invoke the shared editor/bridge, and need no editor mutation window.
    # Save also writes only the isolated stage directory. Final publication
    # creates new files and applies the shared JSON transaction; no editor API.
    $hairProject=if($Stage -eq 'Save'){"$hairRoot/StageHost/HelmetHairStageHost.uproject"}else{"$hairRoot/NativeReadHost/HelmetNativeReadHost.uproject"}
    $hairArgs=@($hairProject,'/Engine/Maps/Entry','-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-NoAssetRegistryCache','-AssetGatherAll=false','-asyncskinnedassetcompilation=0','-asyncstaticmeshcompilation=0','-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',"-abslog=$hairRoot/$Stage-$hairRun.log")
    if($Stage -eq 'HairEnvelope'){$hairArgs+='-EnablePlugins=HairEnvelope';$hairArgs+='-run=HairEnvelope'}
    else {
        $hairArgs+='-DisablePlugins=HairEnvelope'
        $hairScript=if($Stage -eq 'SourceHead'){'helmet_hair_source_head.py'}elseif($Stage -eq 'Rendering'){'helmet_hair_rendering.py'}else{'helmet_hair_save.py'}
        $hairArgs+='-run=pythonscript';$hairArgs+="-script=D:/FPS3D/FPSGAME/Tools/ModernTacticalSet/$hairScript"
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @hairArgs *> "$hairRoot/$Stage-$hairRun.txt"
    $hairExit=$LASTEXITCODE;Write-Output "$Stage exit=$hairExit log=$hairRoot/$Stage-$hairRun.log";exit $hairExit
} finally {if($hairHeld){$hairGate.ReleaseMutex()};$hairGate.Dispose()}
