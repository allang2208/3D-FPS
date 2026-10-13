$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskReport=[ordered]@{stage='waiting_for_existing_build';targets=@();tests_run=$false}
$taskReceipt=Join-Path $taskRoot 'Receipts/native-build.json'
function Save-TaskBuild { $taskReport | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $taskReceipt -Encoding utf8 }
Save-TaskBuild
foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
    do {
        $taskOther=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -like '*UnrealBuildTool*' })
        if($taskOther.Count -gt 0) {
            Write-Output "Waiting for the active build before $taskTarget"
            $taskOther | ForEach-Object { Wait-Process -Id $_.ProcessId -Timeout 40 -ErrorAction SilentlyContinue }
        }
    } while($taskOther.Count -gt 0)
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
        $taskReport.stage='preserved_running_editor';Save-TaskBuild;exit 2
    }
    $taskReport.stage='building_'+$taskTarget;Save-TaskBuild
    $taskLog=Join-Path $taskRoot "Receipts/build-$taskTarget.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $taskTarget Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' '-NoHotReload' '-NoHotReloadFromIDE' "-Log=$taskLog" *> (Join-Path $taskRoot "Receipts/build-$taskTarget-stdout.log")
    $taskExit=$LASTEXITCODE
    $taskReport.targets+=@{target=$taskTarget;exit_code=$taskExit;log=$taskLog};Save-TaskBuild
    Write-Output "$taskTarget BUILD_EXIT=$taskExit"
    if($taskExit -ne 0){$taskReport.stage='build_failed';Save-TaskBuild;exit $taskExit}
}
$taskReport.stage='editor_and_game_built';Save-TaskBuild
