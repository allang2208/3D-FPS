$ErrorActionPreference='Stop'
$warhammerProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$warhammerBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
while($warhammerOthers=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
    foreach($warhammerProcess in $warhammerOthers) {
        Write-Output ('Waiting for active UBT process '+$warhammerProcess.ProcessId)
        try { Wait-Process -Id $warhammerProcess.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
    }
}
while($warhammerCommandlets=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' })) {
    foreach($warhammerCommandlet in $warhammerCommandlets) {
        Write-Output ('Waiting for active project commandlet '+$warhammerCommandlet.ProcessId)
        try { Wait-Process -Id $warhammerCommandlet.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
    }
}
if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") {
    throw 'Editor is running. Preserve its state; do not overwrite its base DLL.'
}
$warhammerLog=Join-Path $PSScriptRoot 'build-FPSGAMEEditor.log'
& $warhammerBuild FPSGAMEEditor Win64 Development ('-Project='+$warhammerProject) -NoHotReloadFromIDE -gather -ForceHeaderGeneration *> $warhammerLog
$warhammerExit=$LASTEXITCODE
@{target='FPSGAMEEditor';exit_code=$warhammerExit;log=$warhammerLog;finished=(Get-Date).ToString('s')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
Write-Output ('FPSGAMEEditor exit='+$warhammerExit)
Get-Content -LiteralPath $warhammerLog -Tail 18
exit $warhammerExit
