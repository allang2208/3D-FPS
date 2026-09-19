$ErrorActionPreference='Stop'
$runeSdkBefore=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' -run=RuneSwordAudit -unattended -nosplash -NullRHI -nosound -multiprocess '-DisablePlugins=ModelContextProtocol,AllToolsets,GameFeatures' ('-Report='+$PSScriptRoot+'\report.txt') ('-abslog='+$PSScriptRoot+'\audit.log') *> (Join-Path $PSScriptRoot 'audit_console.log')
    $runeResult=$LASTEXITCODE
} finally { $env:UE_SKIP_UBT_SDK_SETUP=$runeSdkBefore }
exit $runeResult
