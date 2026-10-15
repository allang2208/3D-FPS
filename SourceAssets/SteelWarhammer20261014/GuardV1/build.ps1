$ErrorActionPreference='Stop'
$quickProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$quickBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$quickResults=@()
foreach($quickTarget in @('FPSGAME','FPSGAMEEditor')) {
    while($quickOthers=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
        foreach($quickProcess in $quickOthers) {
            Write-Output ('Waiting for active UBT process '+$quickProcess.ProcessId)
            try { Wait-Process -Id $quickProcess.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
        }
    }
    while($quickCommandlets=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { ($_.CommandLine -replace '/','\') -match [regex]::Escape($quickProject) })) {
        foreach($quickCommandlet in $quickCommandlets) {
            Write-Output ('Waiting for project commandlet '+$quickCommandlet.ProcessId)
            try { Wait-Process -Id $quickCommandlet.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
        }
    }
    if($quickTarget -eq 'FPSGAMEEditor' -and (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'")) {throw 'Game build saved; preserve the open editor before compiling its base DLL.'}
    $quickLog=Join-Path $PSScriptRoot ('build-'+$quickTarget+'.log')
    & $quickBuild $quickTarget Win64 Development ('-Project='+$quickProject) -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 *> $quickLog
    $quickExit=$LASTEXITCODE
    $quickResults+=@{target=$quickTarget;exit_code=$quickExit;log=$quickLog;finished=(Get-Date).ToString('s')}
    @{targets=$quickResults;complete=($quickResults.Count -eq 2 -and $quickExit -eq 0)} | ConvertTo-Json -Depth 4 |
        Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
    Write-Output ($quickTarget+' exit='+$quickExit)
    Get-Content -LiteralPath $quickLog -Tail 18
    if($quickExit -ne 0) {exit $quickExit}
}
