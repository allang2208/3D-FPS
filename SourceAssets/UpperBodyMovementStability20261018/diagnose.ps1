param([Parameter(Mandatory=$true)][string]$Phase)
$ErrorActionPreference='Stop'
$task='D:/FPS3D/FPSGAME/SourceAssets/UpperBodyMovementStability20261018'
$out=Join-Path $task ($Phase+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $out | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$oldSdk=$env:UE_SKIP_UBT_SDK_SETUP
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch remained busy'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=BowSkillTrainingAudit' '-UpperBodyContinuity' "-Report=$out/poses.json" '-unattended' '-nullrhi' '-nosound' '-nosplash' '-nop4' '-NoShaderCompile' '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$out/engine.log" '-stdout' '-FullStdOutLogOutput' *> "$out/console.log"
    $code=$LASTEXITCODE
    @{exit_code=$code;directory=$out;rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath "$task/$Phase-receipt.json" -Encoding utf8
    Get-Content "$out/console.log" -Tail 6
    exit $code
}finally{$env:UE_SKIP_UBT_SDK_SETUP=$oldSdk;if($held){$gate.ReleaseMutex()};$gate.Dispose()}
