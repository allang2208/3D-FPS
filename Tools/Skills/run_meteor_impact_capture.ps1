param([Parameter(Mandatory=$true)][string]$Stage)
$ErrorActionPreference='Stop'
$meteorRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$meteorOut=Join-Path $meteorRoot ('SourceAssets/MeteorVisualReview20261114/'+$Stage)
[IO.Directory]::CreateDirectory($meteorOut) | Out-Null
$meteorHost=Join-Path $meteorRoot 'SourceAssets/MeteorVisualReview20261114/RenderHost/DragonBreathAuthor.uproject'
$meteorArgs=@(('"'+$meteorHost+'"'),'-run=MeteorImpactCapture',('"-Out='+$meteorOut+'"'),
    '-AllowCommandletRendering','-RenderOffscreen','-NoTextureStreaming','-unattended','-nop4','-nosplash','-nosound',
    '-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false',
    '-ini:Engine:[/Script/Engine.RendererSettings]:r.Substrate=True',
    '-ini:Engine:[/Script/Engine.RendererSettings]:r.Substrate.ProjectGBufferFormat=0',
    '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
    ('"-abslog='+(Join-Path $meteorOut 'render.log')+'"'))
# Read-only rendering: no save calls, game instance, player profile or live map.
$meteorProc=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $meteorArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $meteorOut 'console.log') -RedirectStandardError (Join-Path $meteorOut 'stderr.log')
Write-Output ('METEOR_RENDER_PID '+$meteorProc.Id)
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
@{exit_code=$meteorExit;output=$meteorOut;offscreen=$true;asset_only=$true;assets_saved=$false;editor_ui_opened=$false} | ConvertTo-Json | Set-Content (Join-Path $meteorOut 'process.json') -Encoding UTF8
if ($meteorExit -ne 0) {throw "Meteor capture failed: $meteorOut"}
Write-Output ('METEOR_IMPACT_CAPTURE_DONE '+$meteorOut)
