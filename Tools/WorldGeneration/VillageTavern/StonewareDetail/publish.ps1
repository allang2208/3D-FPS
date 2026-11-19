param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$root=(Resolve-Path "$PSScriptRoot/../../../..").Path
$stage=Join-Path $root 'Saved/VillageTavern/StonewareDetailHost'
$content=Join-Path $stage 'Content/WorldGeneration/VillageTavern'
New-Item -ItemType Directory -Path $content,"$stage/Config" -Force | Out-Null
$uproject=Join-Path $stage 'StonewareDetail.uproject'
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
    @{Name='PythonScriptPlugin';Enabled=$true},
    @{Name='EditorScriptingUtilities';Enabled=$true}
)} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $uproject -Encoding UTF8
'[ConsoleVariables]','Interchange.FeatureFlags.Import.FBX=0' |
    Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding UTF8
foreach($directory in 'Service','StonewareDetail'){
    $target=Join-Path "$root/Content/WorldGeneration/VillageTavern" $directory
    $link=Join-Path $content $directory
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    if(!(Test-Path -LiteralPath $link)){
        New-Item -ItemType Junction -Path $link -Target $target | Out-Null
    }
}
$log=Join-Path $stage 'Import.log'
$entry="$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe"
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    try{$held=$mutex.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
    & $entry $uproject /Engine/Maps/Entry -run=pythonscript "-script=$PSScriptRoot/import_stoneware.py" -unattended -nop4 -nosound -NullRHI -nosplash -Multiprocess -NoAssetRegistryCacheWrite -AssetGatherAll=false -ddc=InstalledNoZenLocalFallback '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' "-abslog=$log" *> "$stage/Console.log"
    if($LASTEXITCODE -ne 0 -or !(Select-String -LiteralPath $log -SimpleMatch 'STONEWARE_DETAIL_SAVED' -Quiet)){
        throw "Stoneware import failed. See $log"
    }
    Write-Output 'Saved the pitcher, tankard, dish and rim sherd to StonewareDetail.'
}finally{
    if($held){$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
