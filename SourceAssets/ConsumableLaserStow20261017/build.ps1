param([ValidateSet('Game','Editor')][string]$Target='Game')
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$taskRoot=Join-Path $projectRoot 'SourceAssets/ConsumableLaserStow20261017'
$name=if($Target -eq 'Game'){'FPSGAME'}else{'FPSGAMEEditor'}
while($true){
    $active=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')})
    if(-not $active.Count){break}
    Write-Output 'Waiting for the existing native build.'
    try{Wait-Process -Id $active[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $active[0].ProcessId -ErrorAction SilentlyContinue){throw}}
}
if($Target -eq 'Editor' -and (Get-Process -Name UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue)){
    Write-Output 'Editor modules are in use; preserve the editor and defer the regular Editor build.';exit 75
}
if($Target -eq 'Game' -and (Get-Process -Name FPSGAME -ErrorAction SilentlyContinue)){
    Write-Output 'Standalone game is in use; preserve it.';exit 75
}
$attempt=Get-Date -Format 'yyyyMMdd-HHmmss'
$out=Join-Path $taskRoot ('Build-'+$attempt+'-'+$Target)
New-Item -ItemType Directory -Path $out | Out-Null
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $name Win64 Development "-Project=$projectRoot/FPSGAME.uproject" '-NoHotReload' '-NoHotReloadFromIDE' '-NoUBA' '-NoUBTMakefiles' '-MaxParallelActions=4' "-Log=$out/build.log" *> "$out/console.log"
$code=$LASTEXITCODE
if($code -ne 0){Write-Output "Build failed; log=$out/console.log";exit $code}
@{target=$name;build='Succeeded';game_run=$false;log="$out/console.log"} | ConvertTo-Json | Set-Content -Encoding UTF8 "$out/result.json"
Write-Output "CONSUMABLE_LASER_BUILD_SAVED $out/result.json"
