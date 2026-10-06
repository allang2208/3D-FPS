$ErrorActionPreference='Stop'
$stockProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$stockBusy=@(Get-CimInstance Win32_Process | Where-Object {
 $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or
 ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
})
if($stockBusy.Count){throw 'Native build is occupied; no editor or build process was stopped.'}
$stockReport=@{tested=$false;targets=@{}}
$stockDir=Join-Path $stockProject 'SourceAssets/LegendaryStock20261006/Integration'
foreach($stockTarget in @('FPSGAMEEditor','FPSGAME')){
 $stockLog=Join-Path $stockDir ("build-$stockTarget-"+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
 & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $stockTarget Win64 Development "-project=$stockProject/FPSGAME.uproject" -NoHotReloadFromIDE *> $stockLog
 $stockResult=$LASTEXITCODE
 $stockReport.targets[$stockTarget]=@{exit_code=$stockResult;log=$stockLog}
 $stockReport | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $stockDir 'native-build-receipt.json') -Encoding UTF8
 Get-Content -LiteralPath $stockLog -Tail 12
 if($stockResult -ne 0){throw "Native build failed: $stockLog"}
}
