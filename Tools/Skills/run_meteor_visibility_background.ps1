param([Parameter(Mandatory=$true)][string]$Script,[Parameter(Mandatory=$true)][string]$Stage,[switch]$MainProject,[string]$OutputRoot='')
$ErrorActionPreference = 'Stop'
$meteorRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$meteorOut = Join-Path $meteorRoot 'SourceAssets/MeteorVisibilityRepair20261114'
if ($OutputRoot) { $meteorOut=[IO.Path]::GetFullPath($OutputRoot) }
[IO.Directory]::CreateDirectory($meteorOut) | Out-Null
$meteorGate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$meteorHeld = $false
try {
    while (-not $meteorHeld) {
        $meteorHeld = $meteorGate.WaitOne([TimeSpan]::FromSeconds(60))
        if (-not $meteorHeld) { Write-Output 'Waiting for shared UE batch; no request submitted.' }
    }
    # A terminated process may remain in the Windows process list with no
    # threads. It cannot own a live editor world or an unsaved in-memory package.
    $meteorEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$null -eq $_.ThreadCount -or $_.ThreadCount -gt 0})
    if ($meteorEditors.Count -gt 0) { throw 'Editor now open; use the existing editor bridge instead.' }
    $meteorStamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $meteorLog = Join-Path $meteorOut ($Stage+'-'+$meteorStamp+'.log')
    $meteorConsole = Join-Path $meteorOut ($Stage+'-'+$meteorStamp+'-console.log')
    $meteorHost = Join-Path $meteorRoot 'SourceAssets/DragonBreath20261013/AuthorHost/DragonBreathAuthor.uproject'
    if ($MainProject) { $meteorHost = Join-Path $meteorRoot 'FPSGAME.uproject' }
    $meteorArgs=@(('"'+$meteorHost+'"'),'/Engine/Maps/Entry','-run=pythonscript',('"-script='+$Script.Replace('\','/')+'"'),
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-NoAssetRegistryCacheWrite','-AssetGatherAll=false',
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache','-ZenDataPath=D:/FPS3D/DerivedDataCache/Zen',('"-abslog='+$meteorLog+'"'))
    $meteorProc=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $meteorArgs -WindowStyle Hidden -PassThru -RedirectStandardOutput $meteorConsole -RedirectStandardError (Join-Path $meteorOut ($Stage+'-'+$meteorStamp+'-stderr.log'))
    Write-Output ('METEOR_AUTHOR_PID '+$meteorProc.Id)
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
    @{exit_code=$meteorExit;log=$meteorLog;script=$Script;interactive_editor_opened=$false;game_started=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $meteorOut ($Stage+'-process.json')) -Encoding UTF8
    if ($meteorExit -ne 0) { throw ('Meteor '+$Stage+' failed; '+$meteorLog) }
    Write-Output ('METEOR_BACKGROUND_DONE '+$meteorLog)
} finally {
    if ($meteorHeld) { $meteorGate.ReleaseMutex() }
    $meteorGate.Dispose()
}
