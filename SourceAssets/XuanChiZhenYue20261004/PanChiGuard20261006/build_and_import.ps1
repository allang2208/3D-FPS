param([switch]$SkipBuild,[switch]$BuildOnly)
$ErrorActionPreference='Stop'
$panchiGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$panchiHeld=$false
try {
    try {$panchiHeld=$panchiGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$panchiHeld=$true}
    if (-not $panchiHeld) {throw 'UE batch queue timeout.'}
    $panchiDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor holds native DLL; preserve its session and build after it closes.'}
        $panchiBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $panchiBusy) {break}
        if ([DateTime]::UtcNow -ge $panchiDeadline) {throw 'Existing build remains active; no new build submitted.'}
        Start-Sleep -Seconds 5
    } while ($true)
    if (-not $SkipBuild) {
        foreach ($panchiTarget in @('FPSGAMEEditor','FPSGAME')) {
            Write-Output "PANCHI_BUILD_BEGIN $panchiTarget"
            & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $panchiTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' *> (Join-Path $PSScriptRoot "build-$panchiTarget.log")
            if ($LASTEXITCODE -ne 0) {throw "Native build failed: $panchiTarget; see its build log."}
            Write-Output "PANCHI_BUILD_SAVED $panchiTarget"
        }
    }
    if ($BuildOnly) {return}
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; import through its current bridge.'}
    $panchiScript=Join-Path $PSScriptRoot 'install_assets.py'
    $panchiArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$panchiScript",'-unattended','-nop4','-nosplash','-nosound','-NullRHI',"-abslog=$PSScriptRoot/asset-import.log",'-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    Write-Output 'PANCHI_IMPORT_BEGIN'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @panchiArgs *> (Join-Path $PSScriptRoot 'asset-import-console.log')
    if ($LASTEXITCODE -ne 0) {throw 'Asset import failed; see asset-import.log.'}
    Write-Output 'PANCHI_ASSETS_SAVED'
} finally {
    if ($panchiHeld) {$panchiGate.ReleaseMutex()};$panchiGate.Dispose()
}
