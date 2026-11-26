param(
    [string]$Engine = 'E:/Program Files (x86)/UE_5.8'
)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$batch = 'F:/FPSGAMEData/ArtProduction/HillsVillageStable/ExpandedYardR42-20261125'
$cache = 'F:/FPSGAMEData/Caches/DerivedDataCache'
New-Item -ItemType Directory -Force -Path $batch | Out-Null
$log = Join-Path $batch 'author.log'
$env:UE_SKIP_UBT_SDK_SETUP = '1'

$opts = @(
    ('"' + $project + '/FPSGAME.uproject"'),
    '/Engine/Maps/Entry',
    '-run=pythonscript',
    ('-script="' + (Join-Path $PSScriptRoot 'expanded_yard_r42.py') + '"'),
    '-unattended', '-NullRHI', '-nosplash', '-nosound', '-nop4',
    '-Multiprocess', '-AssetGatherAll=false', '-NoAssetRegistryCacheWrite',
    '-asyncStaticMeshCompilation=0',
    ('-LocalDataCachePath=' + $cache),
    ('-ZenDataPath=' + $cache + '/Zen'),
    ('-ini:Engine:[VirtualTextureChunkDDCCache]:Path=' + $cache + '/VT'),
    ('-abslog="' + $log + '"'),
    '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False'
)
$proc = Start-Process -WindowStyle Hidden -PassThru -Wait -FilePath "$Engine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" -ArgumentList $opts
if ($proc.ExitCode -ne 0) {
    Get-Content -LiteralPath $log -Tail 40
    throw "ExpandedYardR42 failed with exit code $($proc.ExitCode). Log: $log"
}
Write-Host "EXPANDED_YARD_R42_OK"
