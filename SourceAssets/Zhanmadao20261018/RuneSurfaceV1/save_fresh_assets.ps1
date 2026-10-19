param([string]$Attempt='fresh-01')
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(15))}
    catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    if(-not $taskHeld){throw 'Fresh material authoring queue timed out.'}
    $taskDeadline=(Get-Date).AddMinutes(15)
    while(Get-CimInstance Win32_Process -Filter "Name = 'dotnet.exe'" | Where-Object {$_.CommandLine -like '*UnrealBuildTool.dll*'}) {
        if((Get-Date) -gt $taskDeadline){throw 'Native build remains active; preserved it.'}
        Start-Sleep -Seconds 5
    }
    # Only brand-new material packages are written. The Python entrypoint refuses
    # existing targets, so an open editor's loaded/unsaved material assets stay owned there.
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$taskRoot/install_assets.py" -ZhanFreshMaterialsOnly -NullRHI -unattended -nop4 -nosplash -nosound "-abslog=$taskRoot/import-commandlet-$Attempt.log" *> "$taskRoot/import-console-$Attempt.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;finished=(Get-Date).ToString('o');fresh_materials_only=$true;game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/commandlet-receipt-$Attempt.json" -Encoding utf8
    if($taskExit -ne 0){throw "Fresh material creation failed ($taskExit)."}
    Write-Output 'ZHANMADAO_NATIVE_RUNE_MATERIALS_SAVED'
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()
}
