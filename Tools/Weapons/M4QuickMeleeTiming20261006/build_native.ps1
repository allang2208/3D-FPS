$ErrorActionPreference='Stop'
$meleeProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$meleeBusy=@(Get-CimInstance Win32_Process | Where-Object {
 $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or
 ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
})
if($meleeBusy.Count){throw 'An editor or native build is running; no process was stopped.'}
$meleeReport=@{tested=$false;targets=@{}}
foreach($meleeTarget in @('FPSGAMEEditor','FPSGAME')){
 $meleeLog=Join-Path $PSScriptRoot ("build-$meleeTarget-"+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
 & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $meleeTarget Win64 Development "-project=$meleeProject/FPSGAME.uproject" -NoHotReloadFromIDE *> $meleeLog
 $meleeResult=$LASTEXITCODE
 $meleeReport.targets[$meleeTarget]=@{exit_code=$meleeResult;log=$meleeLog}
 $meleeReport | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'native-build-receipt.json') -Encoding UTF8
 Get-Content -LiteralPath $meleeLog -Tail 12
 if($meleeResult -ne 0){throw "Native build failed: $meleeLog"}
}
