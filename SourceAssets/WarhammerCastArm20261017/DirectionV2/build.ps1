$ErrorActionPreference='Stop'
$taskResults=@()
foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
    while($taskActive=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build.bat')})) {
        Write-Output ('Waiting for active native build '+($taskActive.ProcessId -join ','))
        foreach($taskProcess in $taskActive){Wait-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue}
    }
    $taskGate=$null;$taskOwns=$false
    try {
        if($taskTarget -eq 'FPSGAMEEditor') {
            $taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
            while(-not $taskOwns){try{$taskOwns=$taskGate.WaitOne(60000)}catch [Threading.AbandonedMutexException]{$taskOwns=$true};if(-not $taskOwns){Write-Output 'Waiting for the UE asset batch before native Editor build.'}}
            while($taskActive=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build.bat')})) {
                foreach($taskProcess in $taskActive){Wait-Process -Id $taskProcess.ProcessId -ErrorAction SilentlyContinue}
            }
            if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME'}){throw 'Editor still open; preserve the user session before linking.'}
        }
        if($taskTarget -eq 'FPSGAME' -and (Get-Process FPSGAME -ErrorAction SilentlyContinue)){throw 'Standalone game is running; preserve it before linking.'}
        $taskLog=Join-Path $PSScriptRoot ('build-'+$taskTarget+'.log')
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=6 *> $taskLog
        $taskCode=$LASTEXITCODE
        $taskResults+=@{target=$taskTarget;exit_code=$taskCode;log=$taskLog;finished=(Get-Date).ToString('s')}
        @{targets=$taskResults} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-receipt.json') -Encoding utf8
        Write-Output ($taskTarget+' exit='+$taskCode);Get-Content -LiteralPath $taskLog -Tail 12
        if($taskCode -ne 0){exit $taskCode}
    } finally {if($taskOwns){$taskGate.ReleaseMutex()};if($taskGate){$taskGate.Dispose()}}
}
