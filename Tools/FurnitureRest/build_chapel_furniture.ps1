param([ValidateSet('FPSGAME','FPSGAMEEditor')][string]$Target='FPSGAME')
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$outDir="$projectRoot/SourceAssets/ChapelFurniture20261116"
$processes=Get-CimInstance Win32_Process
if ($processes | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' }) {
    throw 'A shared Unreal build is already active. Keep it intact and retry later.'
}
if ($Target -eq 'FPSGAMEEditor' -and ($processes | Where-Object { $_.Name -match '^UnrealEditor(?:-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME' })) {
    throw 'The project editor DLL is in use. Keep that process intact and retry after it exits.'
}
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $Target Win64 Development "-Project=$projectRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -NoUBALocal -NoXGE -NoSNDBS -NoFASTBuild -MaxParallelActions=2 "-Log=$outDir/$Target-build.log" *> "$outDir/$Target-build-stdout.log"
$buildExit=$LASTEXITCODE
@{target=$Target;exit_code=$buildExit;finished=(Get-Date).ToString('o');game_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$outDir/$Target-build.json" -Encoding utf8
Write-Output "CHAPEL_FURNITURE_BUILD $Target EXIT=$buildExit"
exit $buildExit
