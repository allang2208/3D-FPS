$ErrorActionPreference='Stop'
$detailsGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$detailsHeld=$false
function Set-DetailsBuildStatus([string]$Phase,[string]$Detail='') {
    @{phase=$Phase;detail=$Detail;updated_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build-status.json" -Encoding utf8
}
try {
    Set-DetailsBuildStatus 'waiting'
    try {$detailsHeld=$detailsGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$detailsHeld=$true}
    if (-not $detailsHeld) {throw 'UE batch queue timeout'}
    $detailsDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor holds the native DLL; preserve its session.'}
        $detailsBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $detailsBusy) {break}
        if ([DateTime]::UtcNow -ge $detailsDeadline) {throw 'An existing native build remains active'}
        Start-Sleep -Seconds 5
    } while ($true)
    foreach ($detailsTarget in @('FPSGAMEEditor','FPSGAME')) {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; preserving loaded DLL.'}
        Set-DetailsBuildStatus 'building' $detailsTarget
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $detailsTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' *> "$PSScriptRoot/build-$detailsTarget.log"
        if ($LASTEXITCODE -ne 0) {throw "Native build failed: $detailsTarget"}
    }
    Set-DetailsBuildStatus 'complete'
    Write-Output 'ATTACHMENT_DETAILS_FORMAT_BUILT'
} catch {
    Set-DetailsBuildStatus 'failed' $_.Exception.Message
    throw
} finally {
    if ($detailsHeld) {$detailsGate.ReleaseMutex()};$detailsGate.Dispose()
}
