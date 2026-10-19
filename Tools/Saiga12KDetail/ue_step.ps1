param([Parameter(Mandatory=$true)][string]$Step)
$ErrorActionPreference='Stop'
$detailProject='D:/FPS3D/FPSGAME'
$detailOutput="$detailProject/SourceAssets/Saiga12KDetail20261018/Receipts"
# Editor binaries must be stable. A Game-only compile does not write them.
# UE 5.8 TargetPlatformManagerModule.cpp:223 honors this process-local flag,
# avoiding the commandlet's otherwise redundant ValidatePlatforms UBT child.
while(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -or (($_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')) -and $_.CommandLine -notmatch '\sFPSGAME\s+Win64\s+Development(?:\s|$)') }).Count -gt 0) { Start-Sleep -Seconds 10 }
$detailPreviousSdk=[Environment]::GetEnvironmentVariable('UE_SKIP_UBT_SDK_SETUP','Process')
try {
 [Environment]::SetEnvironmentVariable('UE_SKIP_UBT_SDK_SETUP','1','Process')
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$detailProject/FPSGAME.uproject" -run=pythonscript "-script=$detailProject/Tools/Saiga12KDetail/$Step.py" -unattended -nop4 -nosplash -nosound -NullRHI '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$detailOutput/$Step.log" *> "$detailOutput/$Step-console.log"
 if($LASTEXITCODE -ne 0){throw "$Step commandlet failed: $LASTEXITCODE"}
} finally { [Environment]::SetEnvironmentVariable('UE_SKIP_UBT_SDK_SETUP',$detailPreviousSdk,'Process') }
