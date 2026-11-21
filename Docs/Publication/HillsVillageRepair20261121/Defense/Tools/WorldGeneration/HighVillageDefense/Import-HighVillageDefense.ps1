param([switch]$WallOnly,[switch]$PortalsOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$engineRoot = 'E:/Program Files (x86)/UE_5.8'
$authoringRun = Join-Path 'F:/FPSGAMEData/ArtProduction/HighVillageDefense/Import' (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$authoringHost = Join-Path $authoringRun 'Host'
$sourceData = Join-Path $projectRoot 'SourceAssets/HillsVillageHighWall20261120/Design01/Authored'
New-Item -ItemType Directory -Path "$authoringHost/Config" -Force | Out-Null
New-Item -ItemType Junction -Path "$authoringHost/Content" -Target "$projectRoot/Content" | Out-Null
# A content-only authoring project mounts the real material packages and writes only
# the five new modules and their owned textures. No game DLL or map is loaded.
@{
    FileVersion=3;EngineAssociation='5.8'
    Plugins=@(
        @{Name='PythonScriptPlugin';Enabled=$true}
        @{Name='GeometryScripting';Enabled=$true}
        @{Name='EditorScriptingUtilities';Enabled=$true}
    )
} | ConvertTo-Json -Depth 4 | Set-Content "$authoringHost/HighVillageAuthor.uproject" -Encoding utf8NoBOM
@'
[/Script/Engine.RendererSettings]
r.VirtualTextures=True
r.AllowStaticLighting=False
'@ | Set-Content "$authoringHost/Config/DefaultEngine.ini" -Encoding utf8NoBOM
$runArgs=@(
    ('"'+$authoringHost+'/HighVillageAuthor.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
    ('-script="'+$PSScriptRoot+'/import_kit.py"'),'-unattended','-NullRHI','-nosplash','-nosound','-nop4','-Multiprocess',
    '-AssetGatherAll=false','-NoAssetRegistryCacheWrite','-LocalDataCachePath=D:/FPS3D/DerivedDataCache',
    '-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
    '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=D:/FPS3D/DerivedDataCache/VT',('-abslog="'+$authoringRun+'/engine.log"')
)
$ownedMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$ownedMutex.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    $env:HIGH_VILLAGE_PROJECT=$projectRoot
    $env:HIGH_VILLAGE_WALL_ONLY=if($WallOnly){'1'}else{'0'}
    $env:HIGH_VILLAGE_PORTALS_ONLY=if($PortalsOnly){'1'}else{'0'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $proc=Start-Process -FilePath "$engineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" -ArgumentList $runArgs -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput "$authoringRun/stdout.log" -RedirectStandardError "$authoringRun/stderr.log"
    if($proc.ExitCode -ne 0){throw "High wall import failed with code $($proc.ExitCode). Log: $authoringRun/engine.log"}
    if(-not (Select-String -LiteralPath "$authoringRun/engine.log" -SimpleMatch 'HIGH_VILLAGE_IMPORT_COMPLETE' -Quiet)){
        throw "High wall import did not finish. Log: $authoringRun/engine.log"
    }
    Write-Output "High village models saved. Receipt: $sourceData/imported.json"
} finally {
    if($held){$ownedMutex.ReleaseMutex()}
    $ownedMutex.Dispose()
}
