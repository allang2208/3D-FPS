param([switch]$LinkOnlyWhenClosed)
$ErrorActionPreference='Stop'
$m24Root='D:/FPS3D/FPSGAME'
$m24Out="$m24Root/SourceAssets/M24CommonOptics20261028"
$m24Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$m24Held=$false
try {
    Write-Output 'Waiting for the existing UE build batch mutex.'
    try{$m24Held=$m24Gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$m24Held=$true}
    if(-not $m24Held){throw 'UE build batch remains occupied; source and saved assets retained.'}
    $m24Editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'})
    $m24CompileOnly=$m24Editors.Count -gt 0
    if($LinkOnlyWhenClosed -and $m24CompileOnly){throw 'Save and close the FPSGAME editor before final DLL linking. No process was stopped.'}
    $m24Mode=if($m24CompileOnly){'objects'}else{'editor'}
    $m24Stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $m24Log="$m24Out/build-$m24Mode-$m24Stamp.log"
    $m24Args=@('FPSGAMEEditor','Win64','Development',"-Project=$m24Root/FPSGAME.uproject",'-WaitMutex','-NoHotReload','-NoHotReloadFromIDE','-NoUBTMakefiles','-ForceHeaderGeneration','-NoUBA','-MaxParallelActions=4',"-Log=$m24Log")
    if($m24CompileOnly){$m24Args+='-NoLink'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' @m24Args *> "$m24Log.stdout.txt"
    $m24Code=$LASTEXITCODE
    @{target='FPSGAMEEditor';mode=$m24Mode;exit_code=$m24Code;log=$m24Log;completed=(Get-Date).ToString('o');runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$m24Out/build-receipt.json" -Encoding utf8
    if($m24Code -ne 0){throw "M24 compile failed: $m24Log"}
    Write-Output "M24 build completed: $m24Mode. No editor or game launched."
} finally {
    if($m24Held){$m24Gate.ReleaseMutex()};$m24Gate.Dispose()
}
