$ErrorActionPreference = 'Stop'
$meteorRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$meteorOut = Join-Path $meteorRoot 'SourceAssets/MeteorImpactReferenceV7_20261114'
$meteorAtlas = Join-Path $meteorOut 'Blast/atlas-manifest.json'
while (-not (Test-Path -LiteralPath $meteorAtlas)) {
    $bake = @(Get-CimInstance Win32_Process -Filter "Name='blender.exe'" | Where-Object { $_.CommandLine -like '*bake_meteor_pressure_v7.py*' })
    if ($bake.Count -eq 0) { throw 'Pressure source production did not complete. Preserve the current impact.' }
    Start-Sleep -Seconds 10
}
$meteorStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$meteorLog = Join-Path $meteorOut ('asset-author-' + $meteorStamp + '.log')
$meteorConsole = Join-Path $meteorOut ('asset-author-console-' + $meteorStamp + '.log')
$meteorHost = Join-Path $meteorRoot 'SourceAssets/DragonBreath20261013/AuthorHost/DragonBreathAuthor.uproject'
$meteorScript = (Join-Path $meteorRoot 'Tools/Skills/build_meteor_reference_v7.py').Replace('\','/')
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $meteorHost /Engine/Maps/Entry -run=pythonscript ('-script=' + $meteorScript) -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -NoAssetRegistryCacheWrite -AssetGatherAll=false -LocalDataCachePath=D:/FPS3D/DerivedDataCache -ZenDataPath=D:/FPS3D/DerivedDataCache/Zen ('-abslog=' + $meteorLog) *> $meteorConsole
$meteorExit = $LASTEXITCODE
@{exit_code=$meteorExit;log=$meteorLog;interactive_editor_opened=$false;game_started=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $meteorOut 'author-process.json') -Encoding UTF8
if ($meteorExit -ne 0) { throw ('Impact author stopped; see ' + $meteorLog) }
& (Join-Path $PSScriptRoot 'build_meteor_reference_v7.ps1')
