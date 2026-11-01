param([string]$Stage='before',[switch]$Render)
$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch busy; diagnosis was not started.'}
    $taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if($taskEditors.Count){throw 'UE process active; diagnosis was not started.'}
    $taskRenderArgs=if($Render){@('-PreviewRender','-AllowCommandletRendering','-RenderOffscreen','-d3d12','-sm6')}else{@('-nullrhi')}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=ThunderHammerRecallAudit -PreviewOnly ('-Out='+$PSScriptRoot+'\'+$Stage+'.json') '-ini:Engine:[ConsoleVariables]:s.StreamableDelegateDelayFrames=0' -unattended -nop4 -nosplash -NoSound -NoLiveCoding @taskRenderArgs -stdout -FullStdOutLogOutput ('-abslog='+$PSScriptRoot+'\'+$Stage+'-engine.log') *> ($PSScriptRoot+'\'+$Stage+'-console.log')
    exit $LASTEXITCODE
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
