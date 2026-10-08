param([string]$Label='before')
$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'UE asset queue timed out.'}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Preserve the running editor.'}
    $out=Join-Path $PSScriptRoot ('LitDiagnosis/'+$Label)
    $log=Join-Path $PSScriptRoot ('native-lit-'+$Label+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=XuanChiSurfaceDiagnosis' "-Out=$out" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-RenderOffscreen' "-abslog=$log" *> ($log+'.console.txt')
    if($LASTEXITCODE -ne 0){throw "Surface diagnosis failed: $log"}
    Write-Output "XUANCHI_SURFACE_DIAGNOSIS_COMPLETE $Label"
} finally {
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
