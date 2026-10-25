$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(600))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset authoring batch busy'}
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'"){throw 'Preserve running editor; cannot open another project authoring process'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=pythonscript ('-script='+$taskRoot+'\author.py') -unattended -nop4 -nosplash -NoSound -NoLiveCoding -RenderOffscreen -stdout -FullStdOutLogOutput ('-abslog='+$taskRoot+'\main-author-engine.log') *> ($taskRoot+'\main-author-console.log')
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;editor_ui_started=$false;tests_run=$false;finished=(Get-Date).ToString('s')} | ConvertTo-Json | Set-Content -LiteralPath ($taskRoot+'\main-author-process.json') -Encoding utf8
    if($taskExit -ne 0){Get-Content -LiteralPath ($taskRoot+'\main-author-console.log') -Tail 28;exit $taskExit}
    & 'C:\Users\allan\AppData\Local\Programs\Python\Python311\python.exe' ($taskRoot+'\publish.py')
    if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
