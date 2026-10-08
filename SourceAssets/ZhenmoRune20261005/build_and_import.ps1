param([switch]$SkipBuild,[switch]$BuildOnly,[switch]$ForceHeaderGeneration)
$ErrorActionPreference='Stop'
$zhenmoGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$zhenmoHeld=$false
try {
    try {$zhenmoHeld=$zhenmoGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$zhenmoHeld=$true}
    if (-not $zhenmoHeld) {throw 'UE batch queue timeout.'}
    $zhenmoDeadline=[DateTime]::UtcNow.AddMinutes(30)
    do {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor holds native DLL; preserve it and finish the normal build after it closes.'}
        $zhenmoBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $zhenmoBusy) {break}
        if ([DateTime]::UtcNow -ge $zhenmoDeadline) {throw 'Existing native build remains active; no new build submitted.'}
        Start-Sleep -Seconds 5
    } while ($true)
    if (-not $SkipBuild) {
        $zhenmoBuildOptions=@()
        if ($ForceHeaderGeneration) {$zhenmoBuildOptions+='-ForceHeaderGeneration'}
        foreach ($zhenmoTarget in @('FPSGAMEEditor','FPSGAME')) {
            Write-Output "ZHENMO_BUILD_BEGIN $zhenmoTarget"
            & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $zhenmoTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' @zhenmoBuildOptions -WaitMutex *> (Join-Path $PSScriptRoot "build-$zhenmoTarget.log")
            if ($LASTEXITCODE -ne 0) {throw "Native build failed: $zhenmoTarget; see its build log."}
            Write-Output "ZHENMO_BUILD_SAVED $zhenmoTarget"
        }
    }
    if ($BuildOnly) {return}
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor opened; save assets through its existing bridge.'}
    $zhenmoScript=Join-Path $PSScriptRoot 'install_assets.py'
    $zhenmoLog=Join-Path $PSScriptRoot 'asset-import.log'
    $zhenmoArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$zhenmoScript",
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI',"-abslog=$zhenmoLog",
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    Write-Output 'ZHENMO_IMPORT_BEGIN'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @zhenmoArgs *> (Join-Path $PSScriptRoot 'asset-import-console.log')
    if ($LASTEXITCODE -ne 0) {throw 'Zhenmo asset authoring failed; see asset-import.log.'}
    # Niagara stack authoring must be finalized from disk in a fresh process.
    $zhenmoRuntimeScript=Join-Path $PSScriptRoot 'RisingMotes/rebuild_runtime.py'
    $zhenmoRuntimeArgs=@('D:/FPS3D/FPSGAME/FPSGAME.uproject','-run=pythonscript',"-script=$zhenmoRuntimeScript",
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI',"-abslog=$PSScriptRoot/particle-runtime-rebuild.log",
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @zhenmoRuntimeArgs *> (Join-Path $PSScriptRoot 'particle-runtime-rebuild-console.log')
    if ($LASTEXITCODE -ne 0) {throw 'Zhenmo Niagara runtime rebuild failed.'}
    Write-Output 'ZHENMO_ASSETS_SAVED'
} finally {
    if ($zhenmoHeld) {$zhenmoGate.ReleaseMutex()}
    $zhenmoGate.Dispose()
}
