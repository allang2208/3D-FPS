# Asset import and the Editor target are already complete. The standalone Game
# target writes its own executable, not the DLLs loaded by editor commandlets.
param()
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$taskRoot=Join-Path $projectRoot 'SourceAssets/LambTwoView20261017'
$editorLog=Join-Path $taskRoot '20261017-091343/FPSGAMEEditor-console.log'
if(-not (Select-String -LiteralPath $editorLog -Pattern '^Result: Succeeded' -Quiet)){throw 'Missing completed Editor build receipt'}
while($true){
    $active=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')})
    if(-not $active.Count){break}
    Write-Output 'Waiting for the existing native build.'
    try{Wait-Process -Id $active[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $active[0].ProcessId -ErrorAction SilentlyContinue){throw}}
}
if(Get-Process -Name FPSGAME -ErrorAction SilentlyContinue){Write-Output 'Standalone game is running; preserve it.';exit 75}
$attempt=Get-Date -Format 'yyyyMMdd-HHmmss'
$out=Join-Path $taskRoot $attempt
New-Item -ItemType Directory -Path $out | Out-Null
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development "-Project=$projectRoot/FPSGAME.uproject" '-NoHotReload' '-NoHotReloadFromIDE' '-MaxParallelActions=4' "-Log=$out/FPSGAME.log" *> "$out/FPSGAME-console.log"
$code=$LASTEXITCODE
if($code -ne 0){Write-Output "Game build failed; log=$out/FPSGAME-console.log";exit $code}
@{builds='Succeeded';targets=@('FPSGAMEEditor','FPSGAME');editor_receipt=$editorLog;game_receipt="$out/FPSGAME-console.log";reused_completed_editor_build=$true;game_run=$false} | ConvertTo-Json | Set-Content -Encoding UTF8 "$out/result.json"
Write-Output "Lamb two-view completed builds: $out/result.json"
