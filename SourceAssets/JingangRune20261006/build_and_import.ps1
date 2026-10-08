param([switch]$SkipBuild,[switch]$BuildOnly)
$ErrorActionPreference='Stop'
$jingangGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$jingangHeld=$false
try {
    try {$jingangHeld=$jingangGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$jingangHeld=$true}
    if (-not $jingangHeld) {throw 'UE batch queue timeout.'}
    $jingangDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor holds native DLL; preserve its session and build after it closes.'}
        $jingangBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $jingangBusy) {break}
        if ([DateTime]::UtcNow -ge $jingangDeadline) {throw 'Existing build remains active; no new build submitted.'}
        Start-Sleep -Seconds 5
    } while ($true)
    if (-not $SkipBuild) {
        foreach ($jingangTarget in @('FPSGAMEEditor','FPSGAME')) {
            Write-Output "JINGANG_BUILD_BEGIN $jingangTarget"
            & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $jingangTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' *> (Join-Path $PSScriptRoot "build-$jingangTarget.log")
            if ($LASTEXITCODE -ne 0) {throw "Native build failed: $jingangTarget; see its build log."}
            Write-Output "JINGANG_BUILD_SAVED $jingangTarget"
        }
    }
    if ($BuildOnly) {return}
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; import through its current bridge.'}
    $jingangScript=Join-Path $PSScriptRoot 'install_assets.py'
    $jingangArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$jingangScript",'-unattended','-nop4','-nosplash','-nosound','-NullRHI',"-abslog=$PSScriptRoot/asset-import.log",'-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    Write-Output 'JINGANG_IMPORT_BEGIN'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @jingangArgs *> (Join-Path $PSScriptRoot 'asset-import-console.log')
    if ($LASTEXITCODE -ne 0) {throw 'Asset import failed; see asset-import.log.'}
    Write-Output 'JINGANG_ASSETS_SAVED'
} finally {
    if ($jingangHeld) {$jingangGate.ReleaseMutex()};$jingangGate.Dispose()
}
