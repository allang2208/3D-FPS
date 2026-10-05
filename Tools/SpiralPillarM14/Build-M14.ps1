param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'),[string]$RecordsRelative='SourceAssets/SpiralPillarM14Meshy20261004/ProductionV01/Records',[switch]$Gather)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskRecords=Join-Path $taskRoot $RecordsRelative
[IO.Directory]::CreateDirectory($taskRecords) | Out-Null
$taskBuild='E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
foreach($taskTarget in $Targets) {
    $taskDeadline=[DateTime]::UtcNow.AddMinutes(15)
    $taskAnnounced=$false
    while($true) {
        $taskProcesses=Get-CimInstance Win32_Process
        $taskBusy=@($taskProcesses | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            $_.Name -eq 'UnrealBuildTool.exe' -or
            ($taskTarget -eq 'FPSGAMEEditor' -and $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME')
        })
        if($taskBusy.Count -eq 0){break}
        if(-not $taskAnnounced){Write-Output ('M14 waiting for existing build or loaded module: '+$taskTarget);$taskAnnounced=$true}
        if([DateTime]::UtcNow -ge $taskDeadline){Write-Output ('M14_BUILD_DEFERRED '+$taskTarget);exit 75}
        Wait-Process -Id $taskBusy.ProcessId -Timeout 45 -ErrorAction SilentlyContinue
    }
    $taskOptions=@()
    if($Gather){$taskOptions+='-gather'}
    $taskDefines=Join-Path $taskRoot ('Intermediate/Build/Win64/x64/'+$taskTarget+'/Development/Core/SharedDefinitions.Core.Cpp20.h')
    if((Test-Path -LiteralPath $taskDefines) -and [IO.File]::ReadAllText($taskDefines) -match '(?m)^#define WITH_LIVE_CODING\s+0\s*$'){$taskOptions+='-NoLiveCoding'}
    $taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $taskLog=Join-Path $taskRecords ('build_'+$taskTarget+'_'+$taskStamp+'.log')
    Write-Output ('M14_BUILD_STARTED '+$taskTarget+' '+$taskLog)
    & $taskBuild $taskTarget Win64 Development ('-Project='+$taskRoot+'/FPSGAME.uproject') -NoHotReload -NoHotReloadFromIDE @taskOptions -MaxParallelActions=4 ('-Log='+$taskLog) *> ($taskLog+'.stdout')
    $taskCode=$LASTEXITCODE
    [IO.File]::WriteAllText((Join-Path $taskRecords ('build_'+$taskTarget+'.json')),(@{target=$taskTarget;exit_code=$taskCode;log=$taskLog;tested=$false}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    Write-Output ('M14_BUILD_FINISHED '+$taskTarget+' '+$taskCode)
    if($taskCode -ne 0){Get-Content -LiteralPath ($taskLog+'.stdout') -Tail 50;exit $taskCode}
}
