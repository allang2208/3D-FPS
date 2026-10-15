param([string]$Script='read_assets.py')
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskLock=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
$taskPreviousSdkSkip=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try {$taskHeld=$taskLock.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch is busy; files preserved'}
    $taskGui=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
    if($taskGui.Count){throw 'Use the existing project editor bridge instead of opening a second host'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $taskStem=[IO.Path]::GetFileNameWithoutExtension($Script)
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=pythonscript' "-script=$taskRoot/$Script" '-unattended' '-nop4' '-nosplash' '-NullRHI' '-nosound' '-NoLiveCoding' "-abslog=$taskRoot/Records/$taskStem-engine.log" *> "$taskRoot/Records/$taskStem-stdout.log"
    $taskCode=$LASTEXITCODE
    Write-Output "M66_V21_$taskStem exit=$taskCode"
    Select-String -LiteralPath "$taskRoot/Records/$taskStem-engine.log" -Pattern 'M66_KNOCKDOWN|Error:|Traceback' | Select-Object -Last 10
    exit $taskCode
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPreviousSdkSkip
    if($taskHeld){$taskLock.ReleaseMutex()};$taskLock.Dispose()
}
