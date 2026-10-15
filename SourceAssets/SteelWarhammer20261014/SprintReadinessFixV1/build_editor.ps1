$ErrorActionPreference='Stop'
$uppercutProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$uppercutBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
while($uppercutOthers=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
    foreach($uppercutProcess in $uppercutOthers) {
        Write-Output ('Waiting for active UBT process '+$uppercutProcess.ProcessId)
        try { Wait-Process -Id $uppercutProcess.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
    }
}
while($uppercutCommandlets=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' })) {
    foreach($uppercutCommandlet in $uppercutCommandlets) {
        Write-Output ('Waiting for active project commandlet '+$uppercutCommandlet.ProcessId)
        try { Wait-Process -Id $uppercutCommandlet.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
    }
}
if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") {
    throw 'Editor is running. Preserve its state; do not overwrite its base DLL.'
}
$uppercutLog=Join-Path $PSScriptRoot 'build-FPSGAMEEditor.log'
& $uppercutBuild FPSGAMEEditor Win64 Development ('-Project='+$uppercutProject) -NoHotReloadFromIDE *> $uppercutLog
$uppercutExit=$LASTEXITCODE
@{target='FPSGAMEEditor';exit_code=$uppercutExit;log=$uppercutLog;finished=(Get-Date).ToString('s')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
Write-Output ('FPSGAMEEditor exit='+$uppercutExit)
Get-Content -LiteralPath $uppercutLog -Tail 18
exit $uppercutExit
