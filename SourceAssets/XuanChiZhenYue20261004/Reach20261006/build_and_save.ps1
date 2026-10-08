param()
$ErrorActionPreference = 'Stop'
$reachGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$reachHeld = $false
try {
    try { $reachHeld = $reachGate.WaitOne([TimeSpan]::FromMinutes(30)) }
    catch [Threading.AbandonedMutexException] { $reachHeld = $true }
    if (-not $reachHeld) { throw 'UE batch wait timed out; no build started.' }
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
        throw 'Editor holds the native DLL. Save and close it before the background build.'
    }
    $reachDeadline = [DateTime]::UtcNow.AddMinutes(30)
    $reachWaiting = $false
    do {
        $reachBusy = Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor-Cmd.exe', 'UnrealBuildTool.exe', 'cl.exe', 'link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if (-not $reachBusy) { break }
        if (-not $reachWaiting) { Write-Output 'Waiting for the existing native build.'; $reachWaiting = $true }
        if ([DateTime]::UtcNow -ge $reachDeadline) { throw 'Existing build remains active.' }
        Start-Sleep -Seconds 5
    } while ($true)
    foreach ($reachTarget in @('FPSGAMEEditor', 'FPSGAME')) {
        if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'Editor opened; preserving its session.' }
        Write-Output "XUANCHI_REACH_BUILD_BEGIN $reachTarget"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $reachTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' *> (Join-Path $PSScriptRoot "build-$reachTarget.log")
        if ($LASTEXITCODE -ne 0) { throw "Native build failed: $reachTarget. See its build log." }
        Write-Output "XUANCHI_REACH_BUILD_SAVED $reachTarget"
    }
    if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'Editor opened; icon import must use its bridge.' }
    $reachIcons = Join-Path (Split-Path $PSScriptRoot) 'FactoryIcons20261006'
    $reachIconScript = Join-Path $reachIcons 'install_icons.py'
    $reachCmdArgs = @('D:/FPS3D/FPSGAME/FPSGAME.uproject', '-run=pythonscript', "-script=$reachIconScript",
        '-unattended', '-nop4', '-nosplash', '-nosound', '-NullRHI', "-abslog=$PSScriptRoot/icon-import.log",
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False')
    Write-Output 'XUANCHI_FACTORY_ICONS_IMPORT_BEGIN'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @reachCmdArgs *> (Join-Path $PSScriptRoot 'icon-import-console.log')
    if ($LASTEXITCODE -ne 0) { throw 'Icon import failed; see icon-import.log.' }
    Write-Output 'XUANCHI_REACH_BUILD_AND_ICONS_SAVED'
} finally {
    if ($reachHeld) { $reachGate.ReleaseMutex() }
    $reachGate.Dispose()
}
