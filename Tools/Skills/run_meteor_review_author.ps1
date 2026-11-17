param([string]$Stage='candidate-author-v2',[string]$Script='')
$ErrorActionPreference='Stop'
$meteorRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$meteorReview=Join-Path $meteorRoot 'SourceAssets/MeteorVisualReview20261114'
if (-not $Script) { $Script=Join-Path $PSScriptRoot 'repair_meteor_visual_scale_20261114.py' }
$meteorArgs=@((Join-Path $meteorReview 'RenderHost/DragonBreathAuthor.uproject'),'/Engine/Maps/Entry',
    '-run=pythonscript',('-script='+$Script),
    '-NullRHI','-unattended','-nop4','-nosplash','-nosound','-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false',
    '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',
    ('-abslog='+(Join-Path $meteorReview ($Stage+'.log'))))
$meteorProc=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $meteorArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $meteorReview ($Stage+'-console.log')) -RedirectStandardError (Join-Path $meteorReview ($Stage+'-stderr.log'))
$meteorProc.ProcessorAffinity=[IntPtr]15;$meteorProc.PriorityClass='AboveNormal'
Write-Output ('METEOR_AUTHOR_PID '+$meteorProc.Id)
while (-not $meteorProc.HasExited) {
    Get-CimInstance Win32_Process -Filter "Name='ShaderCompileWorker.exe'" | Where-Object {$_.ParentProcessId -eq $meteorProc.Id} | ForEach-Object {
        $meteorWorker=Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
        if ($meteorWorker) {$meteorWorker.ProcessorAffinity=[IntPtr]15;$meteorWorker.PriorityClass='AboveNormal'}
    }
    Start-Sleep -Seconds 2;$meteorProc.Refresh()
}
$meteorProc.WaitForExit()
if ($meteorProc.ExitCode -ne 0) {throw ('Meteor author failed: '+$Stage)}
Write-Output ('METEOR_AUTHOR_DONE '+$Stage)
