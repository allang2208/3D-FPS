$ErrorActionPreference='Stop'
$taskRoot=$PSScriptRoot
$taskProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$taskBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$taskCmd='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$taskReceipt=@()
# Import's automatic SDK query uses the same UBT mutex. Let both finish first.
while($taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
    ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -like '*SteelWarhammer20261014*ModulesV1*import_modules.py*')
})) {
    foreach($taskProcess in $taskBusy) {
        try { Wait-Process -Id $taskProcess.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] {}
    }
}
$taskImport=Get-Content -LiteralPath (Join-Path $taskRoot 'import_receipt.json') -Raw | ConvertFrom-Json
if(-not $taskImport.complete){throw 'Module asset import did not complete.'}
foreach($taskTarget in @('FPSGAMEEditor','FPSGAME')) {
    while($taskBusy=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'})) {
        foreach($taskProcess in $taskBusy) {try {Wait-Process -Id $taskProcess.ProcessId -ErrorAction Stop} catch [Microsoft.PowerShell.Commands.ProcessCommandException] {}}
    }
    if($taskTarget -eq 'FPSGAMEEditor' -and (Get-Process UnrealEditor -ErrorAction SilentlyContinue)){throw 'Editor is open; preserve it and defer the base Editor DLL build.'}
    $taskLog=Join-Path $taskRoot ('build-final-'+$taskTarget+'.log')
    & $taskBuild $taskTarget Win64 Development ('-Project='+$taskProject) -NoHotReloadFromIDE *> $taskLog
    $taskExit=$LASTEXITCODE
    $taskReceipt+=@{target=$taskTarget;exit_code=$taskExit;log=$taskLog;finished=(Get-Date).ToString('s')}
    $taskReceipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskRoot 'build_receipt.json') -Encoding utf8
    if($taskExit -ne 0){Get-Content -LiteralPath $taskLog -Tail 30;exit $taskExit}
    Write-Output ($taskTarget+' build completed')
    if($taskTarget -eq 'FPSGAMEEditor') {
        & $taskCmd $taskProject -run=FrostSwordModuleAuthoring ('-Folder='+$taskRoot) `
            '-StaticMesh=/Game/Weapons/SteelWarhammer20261014/SM_SteelWarhammer' `
            '-SkeletalMesh=/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1' `
            '-Material=M_SteelWarhammerSurface' `
            '-Output=D:\FPS3D\FPSGAME\Content\ColdSteelData\warhammer-modules.json' `
            -unattended -nop4 -nosplash -nosound -NullRHI ('-abslog='+$taskRoot+'\mount-engine.log') *> (Join-Path $taskRoot 'mount-commandlet.log')
        $taskExit=$LASTEXITCODE
        @{exit_code=$taskExit;log=(Join-Path $taskRoot 'mount-engine.log');tested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRoot 'mount_receipt.json') -Encoding utf8
        if($taskExit -ne 0){Get-Content -LiteralPath (Join-Path $taskRoot 'mount-engine.log') -Tail 30;exit $taskExit}
        Write-Output 'Warhammer mounting catalog authored'
    }
}
