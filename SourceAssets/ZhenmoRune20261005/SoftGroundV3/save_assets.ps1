$ErrorActionPreference='Stop'
$zhenmoGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$zhenmoHeld=$false
try {
    try {$zhenmoHeld=$zhenmoGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$zhenmoHeld=$true}
    if (-not $zhenmoHeld) {throw 'UE asset queue timeout.'}
    $zhenmoDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'An editor is active; use its existing bridge for this asset batch.'}
        $zhenmoBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $zhenmoBusy) {break}
        if ([DateTime]::UtcNow -ge $zhenmoDeadline) {throw 'Existing native build remains active; asset batch deferred.'}
        Start-Sleep -Seconds 5
    } while ($true)
    $zhenmoScript=Join-Path $PSScriptRoot 'save_visuals.py'
    $zhenmoLog=Join-Path $PSScriptRoot 'asset-commandlet.log'
    $zhenmoArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$zhenmoScript",
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI',"-abslog=$zhenmoLog",
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @zhenmoArgs *> (Join-Path $PSScriptRoot 'asset-console.log')
    if ($LASTEXITCODE -ne 0) {throw 'Soft ground authoring failed; see asset-commandlet.log.'}
    Write-Output 'ZHENMO_SOFT_GROUND_AND_MOTES_SAVED'
} finally {
    if ($zhenmoHeld) {$zhenmoGate.ReleaseMutex()}
    $zhenmoGate.Dispose()
}
