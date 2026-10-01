param([string]$Script='read_assets.py',[string]$Label='read',[switch]$CompileShaders)
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$priorSdkSetup=$env:UE_SKIP_UBT_SDK_SETUP
try {
    while(-not $held) {
        try {$held=$gate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$held=$true}
        if(-not $held){Write-Output 'Waiting for the asset authoring batch lock.'}
    }
    $editors=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'"
    if($editors | Where-Object {$_.CommandLine -like '*FPSGAME*' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)'}) {
        throw 'An FPSGAME editor/commandlet is active; preserve it and use the existing bridge or wait.'
    }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $renderArgs=if($CompileShaders){@('-AllowCommandletRendering','-RenderOffscreen')}else{@('-nullrhi')}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
        'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=pythonscript "-script=$taskRoot\$Script" `
        -unattended -nop4 -nosplash @renderArgs -nosound "-abslog=$taskRoot\$Label-commandlet.log"
    exit $LASTEXITCODE
} finally {$env:UE_SKIP_UBT_SDK_SETUP=$priorSdkSetup;if($held){$gate.ReleaseMutex()};$gate.Dispose()}
