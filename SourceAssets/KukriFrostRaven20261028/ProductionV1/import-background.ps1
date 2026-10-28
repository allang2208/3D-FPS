$ErrorActionPreference='Stop'
$ravenProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$ravenEditor=@(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('/','\').Contains($ravenProject) })
if ($ravenEditor.Count) {
    if ($ravenEditor | Where-Object {$_.Name -eq 'UnrealEditor-Cmd.exe'}) { throw 'A project commandlet is active; preserve its asset batch.' }
    $ravenOutput=Join-Path $PSScriptRoot ('import-bridge-'+[Guid]::NewGuid().ToString('N')+'.txt')
    & 'D:\FPS3D\FPSGAME\Tools\AssetPipeline\mcp_call_codex.ps1' -PythonScript (Join-Path $PSScriptRoot 'import_assets.py') -OutputFile $ravenOutput -MaxOutputChars 1800 -QueueWaitSeconds 60
    exit $LASTEXITCODE
}
$ravenPreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $ravenProject -run=pythonscript "-script=$PSScriptRoot\import_assets.py" -unattended -nosplash -nullrhi -nosound -NoLiveCoding "-abslog=$PSScriptRoot\import-commandlet.log" *> (Join-Path $PSScriptRoot 'import-console.log')
    $ravenExit=$LASTEXITCODE
} finally {
    if ($null -eq $ravenPreviousSDK) { Remove-Item Env:UE_SKIP_UBT_SDK_SETUP -ErrorAction SilentlyContinue } else { $env:UE_SKIP_UBT_SDK_SETUP=$ravenPreviousSDK }
}
exit $ravenExit
