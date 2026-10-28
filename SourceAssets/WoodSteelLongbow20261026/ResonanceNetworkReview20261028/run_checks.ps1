$ErrorActionPreference='Stop'
$reviewRoot='D:/FPS3D/FPSGAME'
$reviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$reviewHeld=$false
try {
    try {$reviewHeld=$reviewGate.WaitOne()} catch [Threading.AbandonedMutexException] {$reviewHeld=$true}
    while(@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealBuildTool.exe','UnrealEditor-Cmd.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }).Count){Start-Sleep -Seconds 5}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Preserve the editor; isolated checks require the completed base DLL.'}
    $reviewLog=Join-Path $PSScriptRoot 'native-checks.log'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        ($reviewRoot+'/FPSGAME.uproject') -run=BowSkillTrainingAudit -BowResonanceReview `
        ('-ReportDir='+$PSScriptRoot) -unattended -nop4 -nosplash -nosound -nullrhi `
        ('-abslog='+$reviewLog) *> ($reviewLog+'.stdout.txt')
    $reviewCode=$LASTEXITCODE
    @{exit_code=$reviewCode;finished=(Get-Date).ToString('s');game_map_started=$false;socket_transport=$false} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $PSScriptRoot 'native-checks-commandlet.json') -Encoding utf8
    Get-Content -LiteralPath ($reviewLog+'.stdout.txt') -Tail 12
    exit $reviewCode
} finally {if($reviewHeld){$reviewGate.ReleaseMutex()};$reviewGate.Dispose()}
