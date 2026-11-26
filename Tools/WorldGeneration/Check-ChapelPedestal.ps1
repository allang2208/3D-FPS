$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$out=Join-Path $project 'SourceAssets/ChapelShrineForecourt20261116/WallStoneR3/Check'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$run=Join-Path $project ('Saved/ChapelSupportCheck/'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
$hostPath=Join-Path $run 'Host'
New-Item -ItemType Directory -Force -Path "$hostPath/Binaries/Win64","$run/Saved/SaveGames","$run/Intermediate" | Out-Null
Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination "$hostPath/FPSGAME.uproject"
Copy-Item -LiteralPath "$project/Config" -Destination "$hostPath/Config" -Recurse
foreach($folder in 'Content','Plugins') {
    New-Item -ItemType Junction -Path (Join-Path $hostPath $folder) -Target (Join-Path $project $folder) | Out-Null
}
foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules') {
    Copy-Item -LiteralPath "$project/Binaries/Win64/$file" -Destination "$hostPath/Binaries/Win64/$file"
}
foreach($name in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin') {
    if(Test-Path -LiteralPath "$project/Intermediate/$name") { Copy-Item -LiteralPath "$project/Intermediate/$name" -Destination "$run/Intermediate/$name" -Recurse }
}
$sourceSave="$project/Saved/SaveGames/TemperateHills_World.sav"
Copy-Item -LiteralPath $sourceSave -Destination "$run/Saved/SaveGames/TemperateHills_World.sav"
$saveHash=(Get-FileHash -LiteralPath $sourceSave -Algorithm SHA256).Hash
$arguments=@(
    ('"'+"$hostPath/FPSGAME.uproject"+'"'),'/Game/GameMaps/L_TemperateHills_Initial',
    '-game','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-unattended','-nosound','-nosplash',
    '-ClearwaterNoMenu','-SkipStartupMenu','-ChapelSupportCheck','-ColdSteelProfile=ChapelSupportCheck',
    '-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
    ('-UserDir="'+$run+'"'),('-abslog="'+"$out/runtime-engine.log"+'"'),
    ('-ExecCmds="t.MaxFPS 30,py '+"$project/Tools/WorldGeneration/check_chapel_pedestal_runtime.py"+'"'),
    '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False'
)
$previousSdkSetting=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $process=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
} finally { $env:UE_SKIP_UBT_SDK_SETUP=$previousSdkSetting }
@{pid=$process.Id;run=$run;source_save_sha256=$saveHash;module_sha256=(Get-FileHash -LiteralPath "$hostPath/Binaries/Win64/UnrealEditor-FPSGAME.dll" -Algorithm SHA256).Hash;arguments=$arguments} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath "$out/runtime-launch.json" -Encoding utf8
Write-Output "CHAPEL_SUPPORT_PID=$($process.Id)"
$deadline=(Get-Date).AddMinutes(12)
while(-not $process.WaitForExit(1000)) {
    if((Get-Date) -gt $deadline) { $process.Kill();throw 'This isolated check exceeded 12 minutes; only its own process was stopped.' }
}
$process.Refresh()
$unchanged=(Get-FileHash -LiteralPath $sourceSave -Algorithm SHA256).Hash -eq $saveHash
@{exit_code=$process.ExitCode;original_world_save_unchanged=$unchanged;completed=(Get-Date -Format o)} | ConvertTo-Json | Set-Content -LiteralPath "$out/runtime-process.json" -Encoding utf8
Write-Output "CHAPEL_SUPPORT_EXIT=$($process.ExitCode) SAVE_UNCHANGED=$unchanged"
if(-not $unchanged -or $process.ExitCode -ne 0) { exit 1 }
if(-not (Test-Path -LiteralPath "$out/runtime.json")) { throw 'Runtime evidence was not produced' }
$report=Get-Content -LiteralPath "$out/runtime.json" -Raw | ConvertFrom-Json
if(-not $report.passed) { Write-Output $report.error;exit 1 }
