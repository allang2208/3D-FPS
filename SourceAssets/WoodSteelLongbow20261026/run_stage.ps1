param([string]$Stage='import_assets',[int]$QueueWaitSeconds=900)
$ErrorActionPreference='Stop'
$bowProject='D:/FPS3D/FPSGAME'
$bowScript=Join-Path $PSScriptRoot ($Stage+'.py')
$bowGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$bowHeld=$false
$bowPreviousSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try {$bowHeld=$bowGate.WaitOne([TimeSpan]::FromSeconds($QueueWaitSeconds))} catch [Threading.AbandonedMutexException] {$bowHeld=$true}
    if(-not $bowHeld){throw 'Asset batch is busy; no request sent.'}
    $bowEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)'})
    if($bowEditors.Count){
        & (Join-Path $bowProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $bowScript -QueueWaitSeconds 0 `
            -OutputFile (Join-Path $PSScriptRoot ($Stage+'-bridge-'+(Get-Date -Format 'yyyyMMdd-HHmmssfff')+'.log')) -MaxOutputChars 2500
        exit $LASTEXITCODE
    }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        (Join-Path $bowProject 'FPSGAME.uproject') '-run=pythonscript' ('-script='+$bowScript) `
        -unattended -nop4 -nosplash -nullrhi -nosound `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        ('-abslog='+(Join-Path $PSScriptRoot ($Stage+'-engine.log'))) -stdout -FullStdOutLogOutput `
        *> (Join-Path $PSScriptRoot ($Stage+'-console.log'))
    $bowExit=$LASTEXITCODE
    @{exit_code=$bowExit;finished=(Get-Date).ToString('s')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot ($Stage+'-commandlet.json')) -Encoding utf8
    Get-Content -LiteralPath (Join-Path $PSScriptRoot ($Stage+'-console.log')) -Tail 12
    exit $bowExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$bowPreviousSdk
    if($bowHeld){$bowGate.ReleaseMutex()};$bowGate.Dispose()
}
