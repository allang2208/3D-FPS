param([Parameter(Mandatory=$true)][string]$Script)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskOut=Join-Path $taskRoot 'SourceAssets/MantisM27/PounceV13'
New-Item -ItemType Directory -Path $taskOut -Force | Out-Null
$taskStamp=(Get-Date -Format 'yyyyMMdd-HHmmss')
if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){
    & (Join-Path $taskRoot 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $Script -OutputFile (Join-Path $taskOut ($taskStamp+'-bridge.txt')) -MaxOutputChars 2500 -QueueWaitSeconds 300
    exit $LASTEXITCODE
}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne()} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Editor appeared; preserve existing process and use bridge.'}
    while($true){
        $taskBuild=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('cl.exe','link.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
        if(-not $taskBuild.Count){break}
        try {Wait-Process -Id $taskBuild[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {}
    }
    $taskLog=Join-Path $taskOut ($taskStamp+'-'+[IO.Path]::GetFileNameWithoutExtension($Script)+'.log')
    Write-Output ('COMMANDLET_LOG '+$taskLog)
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' (Join-Path $taskRoot 'FPSGAME.uproject') '-run=pythonscript' ('-script='+$Script) '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' ('-abslog='+$taskLog) *> ($taskLog+'.stdout.txt')
    $taskExit=$LASTEXITCODE
    Get-Content -LiteralPath $taskLog -Tail 8
    exit $taskExit
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
