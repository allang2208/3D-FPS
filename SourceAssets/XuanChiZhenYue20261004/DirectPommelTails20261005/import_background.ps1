$ErrorActionPreference='Stop'
$assetGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$assetGateHeld=$false
try {
    try {$assetGateHeld=$assetGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$assetGateHeld=$true}
    if (-not $assetGateHeld) {throw 'UE asset queue timeout; import has not started.'}
    $importDeadline=[DateTime]::UtcNow.AddMinutes(20)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
            throw 'An editor is running; use its existing bridge for asset saving.'
        }
        $assetBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $assetBusy) {break}
        if ([DateTime]::UtcNow -ge $importDeadline) {throw 'Background asset queue remains occupied; import has not started.'}
        Start-Sleep -Seconds 5
    } while ($true)
    $importScript=Join-Path $PSScriptRoot 'install_assets.py'
    $importLog=Join-Path $PSScriptRoot 'asset-import.log'
    $importArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$importScript",
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI',"-abslog=$importLog",
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    Write-Output 'XUANCHI_DIRECT_TAIL_IMPORT_BEGIN'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @importArgs *> (Join-Path $PSScriptRoot 'asset-import-console.log')
    if ($LASTEXITCODE -ne 0) {throw 'Asset import failed; see asset-import.log.'}
    Write-Output 'XUANCHI_DIRECT_TAIL_ASSETS_SAVED'
} finally {
    if ($assetGateHeld) {$assetGate.ReleaseMutex()}
    $assetGate.Dispose()
}
