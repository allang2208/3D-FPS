param([string]$Attempt=(Get-Date -Format 'yyyyMMdd-HHmmss'))
$ErrorActionPreference='Stop'
$bowRoot='D:/FPS3D/FPSGAME'
$bowOut=Join-Path $PSScriptRoot ('Isolated/'+$Attempt)
New-Item -ItemType Directory -Force -Path $bowOut | Out-Null
$bowGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$bowHeld=$false
$bowSdk=$env:UE_SKIP_UBT_SDK_SETUP
try{
    try{$bowHeld=$bowGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$bowHeld=$true}
    if(-not $bowHeld){throw 'UE batch remained busy.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$bowRoot/FPSGAME.uproject" `
        -run=BowSkillTrainingAudit -SparrowPresentation "-ReportDir=$bowOut" -unattended -nullrhi -nosound -nosplash -nop4 -NoShaderCompile `
        '-DPCVars=s.StreamableDelegateDelayFrames=0' `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        "-abslog=$bowOut/engine.log" -stdout -FullStdOutLogOutput *> "$bowOut/console.log"
    $code=$LASTEXITCODE
    @{exit_code=$code;directory=$bowOut;rendered=$false;socket_transport=$false} | ConvertTo-Json | Set-Content -Encoding utf8 "$PSScriptRoot/isolated-receipt.json"
    Get-Content "$bowOut/console.log" -Tail 10
    exit $code
}finally{
    $env:UE_SKIP_UBT_SDK_SETUP=$bowSdk
    if($bowHeld){$bowGate.ReleaseMutex()};$bowGate.Dispose()
}
