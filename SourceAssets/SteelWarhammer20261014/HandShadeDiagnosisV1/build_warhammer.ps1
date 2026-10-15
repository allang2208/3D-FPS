$ErrorActionPreference='Stop'
$warhammerRoot=$PSScriptRoot
$warhammerProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$warhammerBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
$warhammerReceipt=@()
foreach($warhammerTarget in @('FPSGAMEEditor')) {
    while($warhammerOther=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
        foreach($warhammerProcess in $warhammerOther) {
            Write-Output ('Waiting for existing build process '+$warhammerProcess.ProcessId)
            try { Wait-Process -Id $warhammerProcess.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
        }
    }
    if($warhammerTarget -eq 'FPSGAMEEditor' -and (Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'")) {
        throw 'Editor is running; preserve its current state. The base DLL build cannot proceed safely.'
    }
    $warhammerLog=Join-Path $warhammerRoot ('build-'+$warhammerTarget+'.log')
    & $warhammerBuild $warhammerTarget Win64 Development ('-Project='+$warhammerProject) -NoHotReloadFromIDE *> $warhammerLog
    $warhammerExit=$LASTEXITCODE
    $warhammerReceipt+=@{target=$warhammerTarget;exit_code=$warhammerExit;log=$warhammerLog;finished=(Get-Date).ToString('s')}
    $warhammerReceipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $warhammerRoot 'build_receipt.json') -Encoding utf8
    Write-Output ($warhammerTarget+' exit='+$warhammerExit)
    if($warhammerExit -ne 0){Get-Content -LiteralPath $warhammerLog -Tail 35;exit $warhammerExit}
}
