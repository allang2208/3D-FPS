$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskPrevious=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try {$taskHeld=$taskGate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch window occupied; no contract test started'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' '-run=TaskTrackingContract' '-LiveCoding=false' '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' "-abslog=$PSScriptRoot/task-contract.log" *> "$PSScriptRoot/task-contract-stdout.log"
    $taskExit=$LASTEXITCODE
    [IO.File]::WriteAllText("$PSScriptRoot/task-contract-exit.json",(@{exit_code=$taskExit;player_save_slots_used=$false;dual_client_gameplay=$false}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    Select-String -LiteralPath "$PSScriptRoot/task-contract.log" -Pattern '\[TaskTrackingContract\]' | Select-Object -Last 10
    exit $taskExit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPrevious
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
