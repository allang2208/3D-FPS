$ErrorActionPreference = 'Stop'
$projectRoot = 'D:\FPS3D\FPSGAME'
$taskRoot = Join-Path $projectRoot 'SourceAssets\HK416QBZ191Furniture20261001'
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
$priorSdkSetup = $env:UE_SKIP_UBT_SDK_SETUP
try {
    while (-not $held) {
        try { $held = $gate.WaitOne(60000) }
        catch [Threading.AbandonedMutexException] { $held = $true }
        if (-not $held) { Write-Output 'Waiting for the asset authoring batch lock.' }
    }
    $editors = Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'"
    if ($editors | Where-Object { $_.CommandLine -like '*FPSGAME*' }) {
        throw 'FPSGAME editor/commandlet is active; preserve it and use its existing bridge.'
    }
    # The target has just been built. Asset-only authoring needs no SDK setup;
    # use UE's process-local switch so startup doesn't enqueue another UBT job.
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
        (Join-Path $projectRoot 'FPSGAME.uproject') -run=pythonscript `
        "-script=$taskRoot\import_assets.py" -unattended -nop4 -nosplash -nullrhi -nosound -UTF8Output `
        "-abslog=$taskRoot\commandlet-import-final.log"
    exit $LASTEXITCODE
}
finally {
    $env:UE_SKIP_UBT_SDK_SETUP = $priorSdkSetup
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
