param([string]$Stage='save_repair')
$ErrorActionPreference='Stop'
$reviewRoot='D:/FPS3D/FPSGAME'
if($Stage -notin @('save_repair','readback','capture_extra')){throw 'Unexpected stage'}
$reviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$reviewHeld=$false
try {
    try {$reviewHeld=$reviewGate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$reviewHeld=$true}
    if(-not $reviewHeld){throw 'Asset channel busy; no commandlet launched'}
    $reviewBusy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($reviewBusy.Count){throw 'Preserve active editor/build; no commandlet launched'}
    $reviewLog=Join-Path $reviewRoot ('SourceAssets/KaitlinBackReview20261117/'+$Stage+'-'+(Get-Date -Format 'HHmmss')+'.log')
    $reviewArgs=@((Join-Path $reviewRoot 'FPSGAME.uproject'),'-run=pythonscript',('-script='+$reviewRoot+'/Tools/KaitlinBackReview/'+$Stage+'.py'),'-nullrhi','-unattended','-nop4','-nosound',('-abslog='+$reviewLog))
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' @reviewArgs *> ($reviewLog+'.stdout.txt')
    $reviewExit=$LASTEXITCODE
    Get-Content -LiteralPath ($reviewLog+'.stdout.txt') -Tail 10
    Write-Output ('KAITLIN_STAGE_EXIT '+$reviewExit+' '+$reviewLog)
    exit $reviewExit
} finally {
    if($reviewHeld){$reviewGate.ReleaseMutex()}
    $reviewGate.Dispose()
}
