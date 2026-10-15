param([ValidateSet('FPSGAME','FPSGAMEEditor')][string]$Target='FPSGAMEEditor')
$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskWaiting=$false
while ($true) {
    $taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        $_.Name -in @('cl.exe','link.exe') -or
        ($Target -eq 'FPSGAMEEditor' -and $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.CommandLine -match 'FPSGAME') -or
        ($Target -eq 'FPSGAME' -and $_.Name -eq 'FPSGAME.exe')
    })
    if ($taskBusy.Count -eq 0) {
        $taskAvailable=$true
        if ($Target -eq 'FPSGAMEEditor') {
            try {
                $taskFile=[IO.File]::Open('D:\FPS3D\FPSGAME\Binaries\Win64\UnrealEditor-FPSGAME.dll','Open','ReadWrite','None')
                $taskFile.Dispose()
            } catch { $taskAvailable=$false }
        }
        if ($taskAvailable) { break }
    }
    if (-not $taskWaiting) { Write-Output 'Waiting for existing build/editor processes to release the target.'; $taskWaiting=$true }
    Start-Sleep -Seconds 5
}
$taskName=if($Target -eq 'FPSGAMEEditor'){'editor'}else{'game'}
$taskLog=Join-Path $taskRoot ($taskName+'-build.log')
$taskConsole=Join-Path $taskRoot ($taskName+'-build-console.log')
Write-Output ('Starting '+$Target)
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' $Target Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskLog" *> $taskConsole
$taskExitCode=$LASTEXITCODE
@{target=$Target;exit_code=$taskExitCode;log=$taskLog;finished=(Get-Date).ToString('s');tests_run=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot ($taskName+'-build-receipt.json')) -Encoding UTF8
Get-Content -LiteralPath $taskConsole -Tail 12
exit $taskExitCode