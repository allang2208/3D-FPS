param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$project=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$stage=Join-Path 'F:/FPSGAMEData/ArtProduction/HillsVillageBakery/Grain' (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
New-Item -ItemType Directory -Path "$stage/Config" -Force | Out-Null
New-Item -ItemType Junction -Path "$stage/Content" -Target "$project/Content" | Out-Null
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
    @{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true},
    @{Name='GeometryScripting';Enabled=$true}
)} | ConvertTo-Json -Depth 5 | Set-Content "$stage/BakeryGrain.uproject" -Encoding utf8
'[ConsoleVariables]', 'Interchange.FeatureFlags.Import.FBX=0' | Set-Content "$stage/Config/DefaultEngine.ini" -Encoding utf8
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$mutex.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $argsList=@(('"'+$stage+'/BakeryGrain.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
        ('-script="'+$PSScriptRoot+'/author_sack.py"'),'-unattended','-NullRHI','-nosplash','-nosound',
        '-nop4','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        '-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',
        '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',
        ('-abslog="'+$stage+'/import.log"'))
    $exe=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    Write-Output "Saving bakery grain sack under $stage"
    $process=Start-Process -FilePath $exe -ArgumentList $argsList -WindowStyle Hidden -Wait -PassThru
    if ($process.ExitCode -ne 0 -or -not (Select-String -LiteralPath "$stage/import.log" -SimpleMatch 'BAKERY_GRAIN_SACK_SAVED' -Quiet)) {
        Select-String -LiteralPath "$stage/import.log" -Pattern 'Traceback|LogPython: Error|Error: Could not' | Select-Object -Last 14
        throw "Bakery prop save failed. $stage/import.log"
    }
    Get-Content -Raw "$project/SourceAssets/HillsVillageBakery/Grain/saved.json"
} finally {if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
