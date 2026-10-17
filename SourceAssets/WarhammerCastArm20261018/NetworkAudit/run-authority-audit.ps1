$ErrorActionPreference='Stop'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while(-not $taskHeld) {
        try {$taskHeld=$taskGate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if(-not $taskHeld){Write-Output 'Waiting for the current UE batch.'}
    }
    while($taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.*FPSGAMEEditor')
    })) {foreach($taskProcess in $taskBusy){Wait-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue}}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Preserve the editor session; run this audit after the formal Editor build.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=SkillNetworkAudit -IceArmorOnly "-AuditOutput=$PSScriptRoot/authority-result.json" -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-UserDir=$PSScriptRoot/CommandletUser/" "-abslog=$PSScriptRoot/authority-audit.log" *> "$PSScriptRoot/authority-audit-stdout.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;finished=(Get-Date).ToString('s');mode='offline authority and replica fixtures, no socket network or rendering'} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/authority-audit-receipt.json" -Encoding utf8
    Write-Output "Ice armor authority audit exit=$taskExit"
    exit $taskExit
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
