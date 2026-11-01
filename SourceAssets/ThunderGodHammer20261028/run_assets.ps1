param([ValidateSet('base','modules','icon')][string]$Stage='base')
$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(60))} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset batch is busy; this batch has not started.'}
    # This batch creates only this task's new ThunderGodHammer packages.
    # Existing weapons/materials are read-only dependencies; no editor-loaded package is replaced.
    $taskScript=if($Stage -eq 'modules'){Join-Path $PSScriptRoot 'ModulesV1/import_assets.py'}elseif($Stage -eq 'icon'){Join-Path $PSScriptRoot 'import_icon.py'}else{Join-Path $PSScriptRoot 'import_base.py'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=pythonscript ('-script='+$taskScript) -unattended -nop4 -nosplash -NoSound -NoLiveCoding -AllowCommandletRendering -RenderOffscreen -d3d12 -sm6 -stdout -FullStdOutLogOutput ('-abslog='+$PSScriptRoot+'\import-'+$Stage+'-engine.log') *> ($PSScriptRoot+'\import-'+$Stage+'-console.log')
    exit $LASTEXITCODE
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
