$ErrorActionPreference='Stop'
$jingangFlameGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$jingangFlameHeld=$false
try {
    try {$jingangFlameHeld=$jingangFlameGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$jingangFlameHeld=$true}
    if (-not $jingangFlameHeld) {throw 'UE batch queue timeout.'}
    $jingangFlameDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor is open; use its existing bridge to save this material.'}
        $jingangFlameBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $jingangFlameBusy) {break}
        if ([DateTime]::UtcNow -ge $jingangFlameDeadline) {throw 'An existing build is still active; no import started.'}
        Start-Sleep -Seconds 5
    } while ($true)
    $jingangFlameArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$PSScriptRoot/install_hud.py",'-unattended','-nop4','-nosplash','-nosound','-NullRHI',"-abslog=$PSScriptRoot/asset-save.log",'-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    Write-Output 'JINGANG_GOLDEN_FLAMES_IMPORT_BEGIN'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @jingangFlameArgs *> (Join-Path $PSScriptRoot 'asset-save-console.log')
    if ($LASTEXITCODE -ne 0) {throw 'Material save failed; see asset-save.log.'}
    Write-Output 'JINGANG_GOLDEN_FLAMES_IMPORT_FINISHED'
} finally {
    if ($jingangFlameHeld) {$jingangFlameGate.ReleaseMutex()}
    $jingangFlameGate.Dispose()
}
