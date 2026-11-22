$ErrorActionPreference='Stop'
$project=(Resolve-Path -LiteralPath "$PSScriptRoot/../../..").Path
$run=Join-Path 'F:/FPSGAMEData/ArtProduction/VillageGunshop/Architecture' (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$hostDir=Join-Path $run 'Author'
$author=Join-Path $PSScriptRoot 'gunshop_shell_author.py'
$exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
New-Item -ItemType Directory -Force -Path "$hostDir/Config" | Out-Null
New-Item -ItemType Junction -Path "$hostDir/Content" -Target "$project/Content" | Out-Null
@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
    @{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true},
    @{Name='GeometryScripting';Enabled=$true})} |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$hostDir/GunshopAuthor.uproject" -Encoding utf8
@('[ConsoleVariables]','r.VirtualTextures=1','r.AllowStaticLighting=0') |
    Set-Content -LiteralPath "$hostDir/Config/DefaultEngine.ini" -Encoding utf8
$params=@(('"'+$hostDir+'/GunshopAuthor.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
    ('-script="'+$author+'"'),'-NullRHI','-unattended','-nosplash','-nosound','-nop4',
    '-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
    '-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',
    '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',
    ('-abslog="'+$run+'/engine.log"'))
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$gate.WaitOne() } catch [Threading.AbandonedMutexException] { $held=$true }
    $env:BAKERY_LEVEL_RUN=$run
    $process=Start-Process -FilePath $exe -ArgumentList $params -WindowStyle Hidden -PassThru
    $process.WaitForExit()
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath "$run/level-saved.json")) {
        throw "Gunshop structure authoring incomplete. See $run/engine.log"
    }
    Get-Content -Raw -LiteralPath "$run/level-saved.json"
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
