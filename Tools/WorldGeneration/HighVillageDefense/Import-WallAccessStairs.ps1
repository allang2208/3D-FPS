param([switch]$Fracture)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$engineCmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$run = Join-Path 'F:/FPSGAMEData/ArtProduction/HighVillageDefense/StairImport' (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$hostDir = Join-Path $run 'Host'
$project = Join-Path $hostDir 'WallAccessStairs.uproject'
New-Item -ItemType Directory -Path "$hostDir/Config" -Force | Out-Null
New-Item -ItemType Junction -Path "$hostDir/Content" -Target "$projectRoot/Content" | Out-Null
@{
    FileVersion=3; EngineAssociation='5.8'
    Plugins=@(
        @{Name='PythonScriptPlugin';Enabled=$true}
        @{Name='GeometryScripting';Enabled=$true}
        @{Name='EditorScriptingUtilities';Enabled=$true}
    )
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $project -Encoding utf8NoBOM
@'
[/Script/Engine.RendererSettings]
r.VirtualTextures=True
r.AllowStaticLighting=False
'@ | Set-Content -LiteralPath "$hostDir/Config/DefaultEngine.ini" -Encoding utf8NoBOM
$runArgs = @(
    ('"'+$project+'"'), '/Engine/Maps/Entry', '-run=pythonscript',
    ('-script="'+$PSScriptRoot+'/import_stairs.py"'), '-unattended', '-NullRHI', '-nosplash', '-nosound',
    '-nop4', '-Multiprocess', '-AssetGatherAll=false', '-NoAssetRegistryCacheWrite',
    '-LocalDataCachePath=D:/FPS3D/DerivedDataCache', '-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
    '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=D:/FPS3D/DerivedDataCache/VT',
    ('-abslog="'+$run+'/engine.log"')
)
$mutex = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $mutex.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    $env:HIGH_VILLAGE_PROJECT = $projectRoot
    $env:HIGH_VILLAGE_STAIR_FRACTURE = if ($Fracture) { "1" } else { "0" }
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    $proc = Start-Process -FilePath $engineCmd -ArgumentList $runArgs -WindowStyle Hidden -Wait -PassThru `
        -RedirectStandardOutput "$run/stdout.log" -RedirectStandardError "$run/stderr.log"
    if ($proc.ExitCode -ne 0) { throw "Stair import failed ($($proc.ExitCode)). See $run/engine.log" }
    $receipt = if ($Fracture) { "fracture_imported.json" } else { "imported.json" }
    Get-Content -Raw -LiteralPath "$projectRoot/SourceAssets/HillsVillageHighWall20261120/Stairs/$receipt"
} finally {
    if ($held) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
