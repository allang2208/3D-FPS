param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'))
$ErrorActionPreference='Stop'
$taskBuild='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$taskRows=@()
foreach($taskTarget in $Targets) {
    $taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
    $taskHeld=$false
    try {
        while(-not $taskHeld){try{$taskHeld=$taskGate.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}}
        do {
            $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
                ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
                ($taskTarget -eq 'FPSGAMEEditor' -and $_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject')
            })
            foreach($taskProcess in $taskBusy) {
                Write-Output ('Waiting for existing '+$taskProcess.Name+' PID '+$taskProcess.ProcessId)
                try{Wait-Process -Id $taskProcess.ProcessId -ErrorAction Stop}catch [Microsoft.PowerShell.Commands.ProcessCommandException]{}
            }
        } while($taskBusy.Count -gt 0)
        $taskApp=if($taskTarget -eq 'FPSGAMEEditor'){'UnrealEditor.exe'}else{'FPSGAME.exe'}
        if(Get-CimInstance Win32_Process -Filter "Name='$taskApp'"){throw ('Preserving running '+$taskApp)}
        $taskLog=Join-Path $PSScriptRoot ('fixed-'+$taskTarget+'.log')
        & $taskBuild $taskTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReloadFromIDE *> $taskLog
        $taskExit=$LASTEXITCODE
        $taskRows+=@{target=$taskTarget;exit_code=$taskExit;log=$taskLog;finished=(Get-Date).ToString('s')}
        $taskRows | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot ('fixed-'+$taskTarget+'-receipt.json')) -Encoding utf8
        Write-Output ($taskTarget+' exit='+$taskExit)
        if($taskExit -ne 0){Get-Content -LiteralPath $taskLog -Tail 35;exit $taskExit}
    } finally {
        if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()
    }
}
