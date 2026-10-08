param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$held=$true}
    if (-not $held) {throw 'UE asset queue timed out; no build or import started.'}
    $deadline=[DateTime]::UtcNow.AddMinutes(20)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'An editor is open; use the existing editor bridge for this batch.'}
        $busy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $busy) {break}
        if ([DateTime]::UtcNow -ge $deadline) {throw 'Native build remains occupied; no build submitted.'}
        Start-Sleep -Seconds 5
    } while ($true)
    if (-not $SkipBuild) {
        Write-Output 'XUANCHI_NATIVE_BUILD_BEGIN'
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex *> (Join-Path $PSScriptRoot 'native-build.log')
        if ($LASTEXITCODE -ne 0) {throw 'Native build failed; see native-build.log. Asset import not started.'}
        Write-Output 'XUANCHI_NATIVE_BUILD_SAVED'
    }
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'An editor opened; use its existing bridge to save assets.'}
    $scriptPath=Join-Path $PSScriptRoot 'import_batch.py'
    $logPath=Join-Path $PSScriptRoot 'asset-import.log'
    $taskArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$scriptPath",
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI',"-abslog=$logPath",
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    Write-Output 'XUANCHI_ASSET_IMPORT_BEGIN'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @taskArgs *> (Join-Path $PSScriptRoot 'asset-import-console.log')
    if ($LASTEXITCODE -ne 0) {throw 'Asset import failed; see asset-import.log.'}
    Write-Output 'XUANCHI_RUNE_GUARD_DELIVERY_SAVED'
} finally {
    if ($held) {$gate.ReleaseMutex()};$gate.Dispose()
}
