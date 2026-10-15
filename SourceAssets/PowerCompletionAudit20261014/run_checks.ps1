$ErrorActionPreference='Stop'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false;$taskPrevious=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try {$taskHeld=$taskMutex.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch lock unavailable; no checks started'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $taskExe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $taskProject='D:/FPS3D/FPSGAME/FPSGAME.uproject'
    $taskResults=@()
    & $taskExe $taskProject '-run=pythonscript' "-script=$PSScriptRoot/audit_assets.py" '-LiveCoding=false' '-unattended' '-nop4' '-nosplash' '-nullrhi' '-nosound' "-abslog=$PSScriptRoot/assets.log" *> "$PSScriptRoot/assets-stdout.log"
    $taskResults+=@{name='saved_map_and_monster_defaults';exit_code=$LASTEXITCODE}
    Write-Output "ASSET_READ_EXIT=$LASTEXITCODE"
    & $taskExe $taskProject '/Engine/Maps/Entry' '-LiveCoding=false' '-unattended' '-NullRHI' '-nosplash' '-nosound' '-nop4' '-NoLoadStartupPackages' '-ExecCmds=Automation RunTests FPSGAME.SceneSearch' '-TestExit=Automation Test Queue Empty' "-ReportExportPath=$PSScriptRoot/Automation" "-abslog=$PSScriptRoot/scene-search.log" *> "$PSScriptRoot/scene-search-stdout.log"
    $taskResults+=@{name='scene_search_automation';exit_code=$LASTEXITCODE}
    Write-Output "SCENE_SEARCH_EXIT=$LASTEXITCODE"
    [IO.File]::WriteAllText("$PSScriptRoot/checks.json",(@{results=$taskResults;read_only_assets=$true;player_save_slots_used=$false;dual_client_gameplay=$false}|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskPrevious
    if($taskHeld){$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
