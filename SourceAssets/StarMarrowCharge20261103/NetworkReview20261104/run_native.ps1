# Read-only isolated commandlet: reads saved clips; writes only task reports and never saves project packages.
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    while(-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(10000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if(-not $taskHeld){continue}
        $busy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*')})
        if($busy.Count){$taskGate.ReleaseMutex();$taskHeld=$false;Start-Sleep -Seconds 10}
    }
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskLog="$PSScriptRoot/native-$taskStamp.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=RuneSwordAudit -StarMarrowMotionOnly "-Report=$PSScriptRoot/native-report.txt" -unattended -nop4 -nosplash -nosound -nullrhi -Multiprocess '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$taskLog" *> "$PSScriptRoot/native-$taskStamp.console.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;log=$taskLog;report="$PSScriptRoot/native-report.txt";editor_gui_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/native-receipt.json" -Encoding utf8
    Get-Content -LiteralPath $taskLog -Tail 18
    exit $taskExit
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
