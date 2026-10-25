$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset batch busy; source production remains saved'}
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'"){throw 'Preserve running editor; close it before the background asset batch'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=pythonscript ('-script='+$taskRoot+'\import_assets.py') -unattended -nop4 -nosplash -NoSound -NoLiveCoding -RenderOffscreen -stdout -FullStdOutLogOutput ('-abslog='+$taskRoot+'\import-engine.log') *> ($taskRoot+'\import-console.log')
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;editor_ui_started=$false;tests_run=$false;finished=(Get-Date).ToString('s')} | ConvertTo-Json | Set-Content -LiteralPath ($taskRoot+'\import-process.json') -Encoding utf8
    if($taskExit -ne 0){Get-Content -LiteralPath ($taskRoot+'\import-console.log') -Tail 24;exit $taskExit}
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
& ($taskRoot+'\build_and_publish.ps1')
exit $LASTEXITCODE
