param([string]$PythonName='install_head.py',[switch]$CompileShaders)
$ErrorActionPreference='Stop'
$runeProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$runeEditors=@(Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe' OR Name = 'UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Replace('/','\').Contains($runeProject) })
if ($runeEditors.Count) { throw 'Preserve the running editor and use the existing authoring bridge.' }
$runePreviousSDK=$env:UE_SKIP_UBT_SDK_SETUP
$runeLog=[System.IO.Path]::GetFileNameWithoutExtension($PythonName)
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    # A rendering RHI compiles the actual desktop material shader; no world is run.
    $runeRhiArgs=if ($CompileShaders) {@('-d3d12','-AllowCommandletRendering')} else {@('-nullrhi')}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $runeProject -run=pythonscript "-script=$PSScriptRoot\$PythonName" -unattended -nosplash @runeRhiArgs -nosound -NoLiveCoding "-abslog=$PSScriptRoot\$runeLog-commandlet.log" *> (Join-Path $PSScriptRoot "$runeLog-console.log")
    $runeExit=$LASTEXITCODE
} finally {
    if ($null -eq $runePreviousSDK) { Remove-Item Env:UE_SKIP_UBT_SDK_SETUP -ErrorAction SilentlyContinue } else { $env:UE_SKIP_UBT_SDK_SETUP=$runePreviousSDK }
}
exit $runeExit
