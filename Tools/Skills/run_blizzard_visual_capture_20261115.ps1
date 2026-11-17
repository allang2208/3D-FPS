param([switch]$SkipBuild,[switch]$ReadOnlyCapture,[string]$Stage='Overview',[float]$EyeZ=500,
    [ValidateSet('RollingV1','StormDomainV2','ChargedV3','StormV2')][string]$CloudVersion='RollingV1')
$ErrorActionPreference='Stop'
$blizzardRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$blizzardOut=Join-Path $blizzardRoot ('SourceAssets/BlizzardVisualReview20261115/'+$Stage)
[IO.Directory]::CreateDirectory($blizzardOut)|Out-Null
$blizzardGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$blizzardHeld=$false
try {
    # Like the existing meteor recorder, a read-only preview can run beside
    # isolated author/game hosts. It never saves packages or opens a user map.
    while (-not $ReadOnlyCapture -and -not $blizzardHeld) {
        $blizzardHeld=$blizzardGate.WaitOne([TimeSpan]::FromSeconds(45))
        if (-not $blizzardHeld) {Write-Output 'Waiting for the shared UE capture/build window.'}
    }
    # A prebuilt capture only reads packages into its own transient world. It
    # can coexist with an editor without touching that editor or its assets.
    # Native builds still require the DLL to be free.
    $blizzardEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        $_.ThreadCount -gt 0 -and $_.CommandLine.Replace('\','/').Contains(($blizzardRoot.Replace('\','/')+'/FPSGAME.uproject'))
    })
    if (-not $SkipBuild -and $blizzardEditors.Count) {throw 'Preserve active UE processes; native capture build has not started.'}
    while (-not $SkipBuild -and @(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool' -and $_.ThreadCount -gt 0}).Count) {
        Write-Output 'Waiting for the existing native build to finish.'
        Start-Sleep -Seconds 15
    }
    if (-not $SkipBuild) {
        $blizzardBuildArgs=@('FPSGAMEEditor','Win64','Development',('-Project='+(Join-Path $blizzardRoot 'FPSGAME.uproject')),
            '-NoHotReload','-NoHotReloadFromIDE','-NoUBA','-MaxParallelActions=4',('-Log='+(Join-Path $blizzardOut 'build.log')))
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' @blizzardBuildArgs *> (Join-Path $blizzardOut 'build-console.log')
        if ($LASTEXITCODE -ne 0) {throw 'Blizzard capture tool build failed; see build-console.log.'}
        Write-Output 'BLIZZARD_CAPTURE_TOOL_BUILT'
    }
    $blizzardLog=Join-Path $blizzardOut 'render.log'
    $blizzardArgs=@(('"'+(Join-Path $blizzardRoot 'FPSGAME.uproject')+'"'),'-run=BlizzardVisualCapture',('"-Out='+$blizzardOut+'"'),('-EyeZ='+$EyeZ.ToString([Globalization.CultureInfo]::InvariantCulture)),('-CloudVersion='+$CloudVersion),
        '-AllowCommandletRendering','-RenderOffscreen','-NoTextureStreaming','-unattended','-nop4','-nosplash','-nosound',
        '-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false',
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',('"-abslog='+$blizzardLog+'"'))
    $blizzardProc=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $blizzardArgs `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $blizzardOut 'console.log') -RedirectStandardError (Join-Path $blizzardOut 'stderr.log')
    $blizzardProc.ProcessorAffinity=[IntPtr]15
    $blizzardProc.PriorityClass='AboveNormal'
    Write-Output ('BLIZZARD_CAPTURE_PID '+$blizzardProc.Id)
    while (-not $blizzardProc.HasExited) {
        Get-CimInstance Win32_Process -Filter "Name='ShaderCompileWorker.exe'" | Where-Object {$_.ParentProcessId -eq $blizzardProc.Id} | ForEach-Object {
            $blizzardWorker=Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
            if($blizzardWorker){$blizzardWorker.PriorityClass='AboveNormal';$blizzardWorker.ProcessorAffinity=[IntPtr]15}
        }
        Start-Sleep -Seconds 3;$blizzardProc.Refresh()
    }
    $blizzardProc.WaitForExit()
    @{exit_code=$blizzardProc.ExitCode;output=$blizzardOut;offscreen=$true;actual_actor='AFPSBlizzardZone';cloud_version=$CloudVersion;
      editor_ui_opened=$false;assets_modified=$false;profile_loaded=$false} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $blizzardOut 'process.json') -Encoding UTF8
    if ($blizzardProc.ExitCode -ne 0) {throw 'Blizzard capture failed; see render.log.'}
    Write-Output ('BLIZZARD_CAPTURE_DONE '+$blizzardOut)
} finally {
    if ($blizzardHeld) {$blizzardGate.ReleaseMutex()}
    $blizzardGate.Dispose()
}
