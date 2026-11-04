$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$batchRoot = Join-Path $projectRoot 'SourceAssets/OneHandAxe20261101/ModulesV1'
$editors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
if ($editors.Count -gt 0) {
    throw 'An Unreal process is active. Keep it intact; use the existing serialized bridge for this import batch.'
}
$env:UE_SKIP_UBT_SDK_SETUP = '1'
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$batchRoot/import_batch.py" -unattended -nop4 -nosplash -NullRHI -nosound "-abslog=$batchRoot/import.log" *> "$batchRoot/import-console.log"
exit $LASTEXITCODE
