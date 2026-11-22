param([string]$Work = 'F:/FPSGAMEData/ArtProduction/HillsVillageBakery/Level',
      [string]$AuthorScript = (Join-Path $PSScriptRoot 'save_bakery_level.py'),
      [switch]$BakeryOnly)
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$run = Join-Path $Work (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$stage = Join-Path $run 'Host'
$binary = Join-Path $stage 'Binaries/Win64'
$cmd = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$gate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne() } catch [Threading.AbandonedMutexException] { $held = $true }
    New-Item -ItemType Directory -Force -Path $binary | Out-Null
    Copy-Item -LiteralPath "$project/FPSGAME.uproject" -Destination $stage
    Copy-Item -Recurse -LiteralPath "$project/Config" -Destination $stage
    foreach ($name in 'Content','Plugins','Shaders') {
        New-Item -ItemType Junction -Path "$stage/$name" -Target "$project/$name" | Out-Null
    }
    $manifest = Get-Content -Raw -LiteralPath "$project/Binaries/Win64/UnrealEditor.modules" | ConvertFrom-Json
    foreach ($name in @('UnrealEditor.modules') + @($manifest.Modules.PSObject.Properties.Value)) {
        Copy-Item -LiteralPath "$project/Binaries/Win64/$name" -Destination $binary
    }
    $env:BAKERY_LEVEL_RUN = $run
    $env:BAKERY_LEVEL_ONLY = if ($BakeryOnly) { '1' } else { '0' }
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    $params = @(('"'+$stage+'/FPSGAME.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',
        ('-script="'+$AuthorScript+'"'),'-unattended','-NullRHI','-nosplash','-nosound',
        '-nop4','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite',
        '-ini:Engine:[SystemSettings]:Editor.AsyncStaticMeshCompilation=0',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorExperimentalSettings]:bEnableAsyncStaticMeshCompilation=False',
        '-LocalDataCachePath=F:/FPSGAMEData/Caches/DerivedDataCache','-ZenDataPath=F:/FPSGAMEData/Caches/DerivedDataCache/Zen',
        '-ini:Engine:[VirtualTextureChunkDDCCache]:Path=F:/FPSGAMEData/Caches/DerivedDataCache/VT',
        ('-abslog="'+$run+'/engine.log"'),'-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    $proc = Start-Process -FilePath $cmd -ArgumentList $params -WindowStyle Hidden -Wait -PassThru
    if ($proc.ExitCode -ne 0 -or -not (Test-Path -LiteralPath "$run/level-saved.json")) {
        Select-String -Path "$run/engine.log" -Pattern 'Traceback|LogPython: Error|Error:|Fatal error' | Select-Object -Last 18
        throw "Bakehouse publication incomplete. See $run/engine.log"
    }
    Get-Content -Raw -LiteralPath "$run/level-saved.json"
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
