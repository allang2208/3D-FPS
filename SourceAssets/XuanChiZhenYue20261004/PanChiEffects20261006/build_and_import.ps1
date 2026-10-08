param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$effectGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$effectHeld=$false
function Set-EffectStatus([string]$Phase,[string]$Detail='') {
    @{phase=$Phase;detail=$Detail;updated_utc=[DateTime]::UtcNow.ToString('o')} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-status.json') -Encoding utf8
}
try {
    Set-EffectStatus 'waiting'
    try {$effectHeld=$effectGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$effectHeld=$true}
    if (-not $effectHeld) {throw 'UE batch queue timeout.'}
    $effectDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor holds native DLL; preserve its session and build after it closes.'}
        $effectBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $effectBusy) {break}
        if ([DateTime]::UtcNow -ge $effectDeadline) {throw 'Existing build remains active; no new build submitted.'}
        Start-Sleep -Seconds 5
    } while ($true)
    if (-not $SkipBuild) {
        foreach ($effectTarget in @('FPSGAMEEditor','FPSGAME')) {
            if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; preserving the loaded DLL.'}
            Set-EffectStatus 'building' $effectTarget
            Write-Output "PANCHI_EFFECT_BUILD_BEGIN $effectTarget"
            & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $effectTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' *> (Join-Path $PSScriptRoot "build-$effectTarget.log")
            if ($LASTEXITCODE -ne 0) {throw "Native build failed: $effectTarget; see its build log."}
            Write-Output "PANCHI_EFFECT_BUILD_SAVED $effectTarget"
        }
    }
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; import through its current bridge.'}
    Set-EffectStatus 'importing'
    $effectScript=Join-Path $PSScriptRoot 'install_assets.py'
    $effectArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$effectScript",'-unattended','-nop4','-nosplash','-nosound','-NullRHI',"-abslog=$PSScriptRoot/asset-import.log",'-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @effectArgs *> (Join-Path $PSScriptRoot 'asset-import-console.log')
    if ($LASTEXITCODE -ne 0) {throw 'Asset import failed; see asset-import.log.'}
    Set-EffectStatus 'complete'
    Write-Output 'PANCHI_EFFECT_BUILD_AND_ASSETS_SAVED'
} catch {
    Set-EffectStatus 'failed' $_.Exception.Message
    throw
} finally {
    if ($effectHeld) {$effectGate.ReleaseMutex()};$effectGate.Dispose()
}
