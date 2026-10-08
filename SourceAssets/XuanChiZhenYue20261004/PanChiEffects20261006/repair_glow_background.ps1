param()
$ErrorActionPreference='Stop'
$glowGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$glowHeld=$false
function Set-GlowStatus([string]$Phase,[string]$Detail='') {
    @{phase=$Phase;detail=$Detail;updated_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/glow-fix-status.json" -Encoding utf8
}
try {
    Set-GlowStatus 'waiting'
    try {$glowHeld=$glowGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$glowHeld=$true}
    if (-not $glowHeld) {throw 'UE batch queue timeout'}
    $glowDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; preserve its session and use its bridge'}
        $glowBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $glowBusy) {break}
        if ([DateTime]::UtcNow -ge $glowDeadline) {throw 'Existing build or commandlet is still active'}
        Start-Sleep -Seconds 5
    } while ($true)
    Set-GlowStatus 'material-repair'
    $glowArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$PSScriptRoot/repair_glow_material.py",'-AllowCommandletRendering','-RenderOffscreen','-d3d12','-unattended','-nop4','-nosplash','-nosound',"-abslog=$PSScriptRoot/glow-fix.log",'-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @glowArgs *> "$PSScriptRoot/glow-fix-console.log"
    if ($LASTEXITCODE -ne 0) {throw 'Guard material repair failed; see glow-fix.log'}
    Set-GlowStatus 'complete'
} catch {
    Set-GlowStatus 'failed' $_.Exception.Message
    throw
} finally {
    if ($glowHeld) {$glowGate.ReleaseMutex()};$glowGate.Dispose()
}
