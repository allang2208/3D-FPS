param([ValidateSet('Game','Editor')][string]$Target='Game',[int[]]$IsolatedEditorPids=@(),[ValidateRange(1,8)][int]$MaxParallelActions=4)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$taskRoot=Join-Path $projectRoot 'SourceAssets/BowConsumableHandoff20261018'
$name=if($Target -eq 'Game'){'FPSGAME'}else{'FPSGAMEEditor'}
while($true){
    $active=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')})
    if(-not $active.Count){break}
    Write-Output 'Waiting for the existing native build.'
    try{Wait-Process -Id $active[0].ProcessId -Timeout 45 -ErrorAction Stop}catch [System.TimeoutException]{}catch{if(Get-Process -Id $active[0].ProcessId -ErrorAction SilentlyContinue){throw}}
}
$loadedEditors=@(Get-Process -Name UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue | Where-Object {
    # A caller may name a verified copied-DLL host. Never exclude a primary
    # project process just because a later process reused that numeric PID.
    if($_.Id -notin $IsolatedEditorPids){return $true}
    $details=Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)"
    if($details.CommandLine -match '[\\/]IsolatedHost[\\/]'){return $false}
    if($details.CommandLine -match '[\\/]AssetHost[\\/]'){
        # This explicitly named engine-only import host has no project module.
        # Re-read loaded modules so a reused PID never exempts the real project.
        $projectModules=@($_.Modules | Where-Object {$_.FileName.Replace('\','/').StartsWith($projectRoot+'/',[StringComparison]::OrdinalIgnoreCase)})
        return $projectModules.Count -gt 0
    }
    return $true
})
if($Target -eq 'Editor' -and $loadedEditors.Count){
    Write-Output 'Editor modules are in use; preserve the editor and defer the regular Editor build.';exit 75
}
if($Target -eq 'Game' -and (Get-Process -Name FPSGAME -ErrorAction SilentlyContinue)){
    Write-Output 'Standalone game is in use; preserve it.';exit 75
}
$attempt=Get-Date -Format 'yyyyMMdd-HHmmss'
$out=Join-Path $taskRoot ('Build-'+$attempt+'-'+$Target)
New-Item -ItemType Directory -Path $out | Out-Null
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $name Win64 Development "-Project=$projectRoot/FPSGAME.uproject" '-NoHotReload' '-NoHotReloadFromIDE' '-NoUBA' '-NoUBTMakefiles' "-MaxParallelActions=$MaxParallelActions" "-Log=$out/build.log" *> "$out/console.log"
$code=$LASTEXITCODE
if($code -ne 0){Write-Output "Build failed; log=$out/console.log";exit $code}
@{target=$name;build='Succeeded';game_run=$false;log="$out/console.log"} | ConvertTo-Json | Set-Content -Encoding UTF8 "$out/result.json"
Write-Output "BOW_CONSUME_BUILD_SAVED $out/result.json"
