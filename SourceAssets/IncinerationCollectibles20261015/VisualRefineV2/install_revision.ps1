$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskProject='D:/FPS3D/FPSGAME'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try {$taskHeld=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Asset batch is busy; revision remains staged'}
    $taskActive=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskProject/FPSGAME.uproject")})
    if(@($taskActive | Where-Object Name -eq 'UnrealEditor.exe').Count){throw 'Preserve the active project editor; install through its batch bridge'}
    foreach($taskProcess in $taskActive){
        Write-Output "Waiting for project commandlet PID $($taskProcess.ProcessId) before replacing stable mesh packages"
        try {[Diagnostics.Process]::GetProcessById($taskProcess.ProcessId).WaitForExit()} catch [ArgumentException] {}
    }
    $taskStillActive=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -and $_.CommandLine.Replace('\','/').Contains("$taskProject/FPSGAME.uproject")})
    if($taskStillActive.Count){throw 'A new project editor operation started; preserve staged revision'}
    & py -3.11 (Join-Path $taskRoot 'Scripts/install_revision.py')
    exit $LASTEXITCODE
} finally {
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
