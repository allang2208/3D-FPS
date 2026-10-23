$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$taskBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$taskReceipt=@()
foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
    while($taskOther=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
        foreach($taskProcess in $taskOther) {
            Write-Output ('Waiting for existing build process '+$taskProcess.ProcessId)
            try { Wait-Process -Id $taskProcess.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
        }
    }
    $taskApp=if($taskTarget -eq 'FPSGAMEEditor'){'UnrealEditor.exe'}else{'FPSGAME.exe'}
    if(Get-CimInstance Win32_Process -Filter "Name='$taskApp'") {
        throw ('Preserving running '+$taskApp+'; cannot replace its binary.')
    }
    $taskLog=Join-Path $taskRoot ('build-'+$taskTarget+'.log')
    & $taskBuild $taskTarget Win64 Development ('-Project='+$taskProject) -NoHotReloadFromIDE *> $taskLog
    $taskExit=$LASTEXITCODE
    $taskReceipt+=@{target=$taskTarget;exit_code=$taskExit;log=$taskLog;finished=(Get-Date).ToString('s')}
    $taskReceipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskRoot 'build_receipt.json') -Encoding utf8
    Write-Output ($taskTarget+' exit='+$taskExit)
    if($taskExit -ne 0){Get-Content -LiteralPath $taskLog -Tail 45;exit $taskExit}
}
