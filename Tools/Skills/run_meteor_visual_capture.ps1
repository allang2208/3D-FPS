param([Parameter(Mandatory=$true)][string]$Stage,[int]$EyeZ=430,[switch]$ReadOnlyCapture)
$ErrorActionPreference='Stop'
$meteorRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$meteorOut=Join-Path $meteorRoot ('SourceAssets/MeteorVisualReview20261114/'+$Stage)
[IO.Directory]::CreateDirectory($meteorOut) | Out-Null
$meteorGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$meteorHeld=$false
try {
    # This commandlet never saves assets or opens a map/profile. Its isolated
    # preview world can read meteor packages while an unrelated author host
    # edits other packages. Asset authoring still uses the shared batch mutex.
    if (-not $ReadOnlyCapture) {
        while (-not $meteorHeld) {
            $meteorHeld=$meteorGate.WaitOne([TimeSpan]::FromSeconds(60))
            if (-not $meteorHeld) { Write-Output 'Waiting for shared UE batch.' }
        }
    }
    if (-not $ReadOnlyCapture -and @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'").Count) {
        throw 'Editor is running; preserve the existing editor and use its bridge.'
    }
    $meteorLog=Join-Path $meteorOut 'render.log'
    $meteorConsole=Join-Path $meteorOut 'console.log'
    $meteorArgs=@(('"'+(Join-Path $meteorRoot 'FPSGAME.uproject')+'"'),'-run=MeteorVisualCapture',('"-Out='+$meteorOut+'"'),('-EyeZ='+$EyeZ),
        '-AllowCommandletRendering','-RenderOffscreen','-NoTextureStreaming','-unattended','-nop4','-nosplash','-nosound',
        '-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false',
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',('"-abslog='+$meteorLog+'"'))
    $meteorProc=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $meteorArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput $meteorConsole -RedirectStandardError (Join-Path $meteorOut 'stderr.log')
    Write-Output ('METEOR_ACTOR_CAPTURE_PID '+$meteorProc.Id)
    $meteorProc.ProcessorAffinity=[IntPtr]15
    $meteorProc.PriorityClass='AboveNormal'
    while (-not $meteorProc.HasExited) {
        Get-CimInstance Win32_Process -Filter "Name='ShaderCompileWorker.exe'" | Where-Object {$_.ParentProcessId -eq $meteorProc.Id} | ForEach-Object {
            $meteorWorker=Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
            if ($meteorWorker) {$meteorWorker.ProcessorAffinity=[IntPtr]15; $meteorWorker.PriorityClass='AboveNormal'}
        }
        Start-Sleep -Seconds 3
        $meteorProc.Refresh()
    }
    $meteorProc.WaitForExit()
    $meteorExit=$meteorProc.ExitCode
    @{exit_code=$meteorExit;output=$meteorOut;offscreen=$true;actual_actor='AFPSMeteorStrike';editor_ui_opened=$false} | ConvertTo-Json | Set-Content (Join-Path $meteorOut 'process.json') -Encoding UTF8
    if ($meteorExit -ne 0) { throw "Capture failed: $meteorLog" }
    Write-Output "METEOR_CAPTURE_DONE $meteorOut"
} finally {
    if ($meteorHeld) { $meteorGate.ReleaseMutex() }
    $meteorGate.Dispose()
}
