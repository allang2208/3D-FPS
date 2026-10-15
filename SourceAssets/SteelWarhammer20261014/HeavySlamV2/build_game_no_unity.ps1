$ErrorActionPreference='Stop'
$warhammerRoot=$PSScriptRoot
while($warhammerOther=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
    foreach($warhammerProcess in $warhammerOther){try {Wait-Process -Id $warhammerProcess.ProcessId -ErrorAction Stop} catch [Microsoft.PowerShell.Commands.ProcessCommandException] {}}
}
$warhammerLog=Join-Path $warhammerRoot 'build-FPSGAME.log'
& 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAME Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' -NoHotReloadFromIDE -DisableUnity *> $warhammerLog
$warhammerExit=$LASTEXITCODE
$warhammerRecords=@(Get-Content -LiteralPath (Join-Path $warhammerRoot 'build_receipt.json') -Raw | ConvertFrom-Json | Where-Object { $_.target -ne 'FPSGAME' })
$warhammerRecords+=@{target='FPSGAME';exit_code=$warhammerExit;extra_args=@('-DisableUnity');log=$warhammerLog;finished=(Get-Date).ToString('s')}
$warhammerRecords | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $warhammerRoot 'build_receipt.json') -Encoding utf8
Write-Output ('FPSGAME exit='+$warhammerExit)
if($warhammerExit -ne 0){Get-Content -LiteralPath $warhammerLog -Tail 30}
exit $warhammerExit
