$ErrorActionPreference='Stop'
$talismanGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$talismanHeld=$false
function Set-TalismanStatus([string]$Phase,[string]$Detail='') {
    @{phase=$Phase;detail=$Detail;updated_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/save-status.json" -Encoding utf8
}
try {
    Set-TalismanStatus 'waiting'
    try {$talismanHeld=$talismanGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$talismanHeld=$true}
    if (-not $talismanHeld) {throw 'UE batch queue timeout'}
    $talismanDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor is active; use its existing bridge for this asset batch.'}
        $talismanBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $talismanBusy) {break}
        if ([DateTime]::UtcNow -ge $talismanDeadline) {throw 'An existing build or commandlet is still active'}
        Start-Sleep -Seconds 5
    } while ($true)
    Set-TalismanStatus 'saving'
    $talismanArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$PSScriptRoot/install_assets.py",'-AllowCommandletRendering','-RenderOffscreen','-d3d12','-unattended','-nop4','-nosplash','-nosound',"-abslog=$PSScriptRoot/asset-save.log",'-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @talismanArgs *> "$PSScriptRoot/asset-console.log"
    if ($LASTEXITCODE -ne 0) {throw 'Talisman asset save failed; see asset-save.log'}
    Set-TalismanStatus 'complete'
    Write-Output 'ZHENMO_TALISMAN_V4_SAVE_COMPLETE'
} catch {
    Set-TalismanStatus 'failed' $_.Exception.Message
    throw
} finally {
    if ($talismanHeld) {$talismanGate.ReleaseMutex()};$talismanGate.Dispose()
}
