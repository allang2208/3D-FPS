$ErrorActionPreference='Stop'
$inspectProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$inspectBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$inspectResults=@()
foreach($inspectTarget in @('FPSGAMEEditor','FPSGAME')) {
    while($inspectOthers=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
        foreach($inspectProcess in $inspectOthers) {
            Write-Output ('Waiting for active UBT process '+$inspectProcess.ProcessId)
            try { Wait-Process -Id $inspectProcess.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
        }
    }
    while($inspectCommandlets=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' })) {
        foreach($inspectCommandlet in $inspectCommandlets) {
            Write-Output ('Waiting for project commandlet '+$inspectCommandlet.ProcessId)
            try { Wait-Process -Id $inspectCommandlet.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
        }
    }
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") {throw 'Editor is running; preserve its state before compiling the base DLL.'}
    $inspectLog=Join-Path $PSScriptRoot ('build-'+$inspectTarget+'.log')
    & $inspectBuild $inspectTarget Win64 Development ('-Project='+$inspectProject) -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 *> $inspectLog
    $inspectExit=$LASTEXITCODE
    $inspectResults+=@{target=$inspectTarget;exit_code=$inspectExit;log=$inspectLog;finished=(Get-Date).ToString('s')}
    @{targets=$inspectResults;complete=($inspectResults.Count -eq 2 -and $inspectExit -eq 0)} | ConvertTo-Json -Depth 4 |
        Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
    Write-Output ($inspectTarget+' exit='+$inspectExit)
    Get-Content -LiteralPath $inspectLog -Tail 18
    if($inspectExit -ne 0) {exit $inspectExit}
}
