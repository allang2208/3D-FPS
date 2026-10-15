$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskPrevious=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try {$taskHeld=$taskGate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch window occupied; no clock test started'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '/Engine/Maps/Entry' '-LiveCoding=false' '-unattended' '-NullRHI' '-nosplash' '-nosound' '-nop4' '-NoLoadStartupPackages' '-ExecCmds=Automation RunTests FPSGAME.PowerNetwork.HangingBellClock' '-TestExit=Automation Test Queue Empty' "-ReportExportPath=$PSScriptRoot/ClockAutomation" "-abslog=$PSScriptRoot/hanging-bell-clock.log" *> "$PSScriptRoot/hanging-bell-clock-stdout.log"
    $taskExit=$LASTEXITCODE
    Write-Output "HANGING_BELL_CLOCK_EXIT=$taskExit"
    exit $taskExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPrevious
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
