$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$editorIds=@(Get-Process -Name 'UnrealEditor','UnrealEditor-Cmd' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
# WMI can retain an exited editor row briefly after its log and process have closed.
$running=Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -in $editorIds -and $_.CommandLine -match 'FPSGAME.uproject' }
if($running){throw 'FPSGAME editor still owns loaded binaries; preserve it and wait for normal exit'}
$log="$project/SourceAssets/DungeonPerformance20260923Batch/Receipts/editor-build.log"
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($log)) | Out-Null
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$project/FPSGAME.uproject" -WaitMutex 2>&1 | Tee-Object -FilePath $log
$code=$LASTEXITCODE
@{target='FPSGAMEEditor Win64 Development';exit_code=$code;log=$log;runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$project/SourceAssets/DungeonPerformance20260923Batch/Receipts/build.json" -Encoding UTF8
exit $code
