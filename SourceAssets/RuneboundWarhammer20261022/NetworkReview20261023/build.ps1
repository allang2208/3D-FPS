param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'),[string]$Attempt='01')
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$ubt='E:/Program Files (x86)/UE_5.8/Engine/Binaries/DotNET/UnrealBuildTool/UnrealBuildTool.dll'
foreach($target in $Targets){
    foreach($p in @(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'})){
        while(Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue){Start-Sleep -Seconds 10}
    }
    if($target -eq 'FPSGAMEEditor'){
        foreach($p in @(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^UnrealEditor(?:-Cmd)?\.exe$' -and $_.CommandLine -like '*FPSGAME.uproject*'})){
            while(Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue){Start-Sleep -Seconds 10}
        }
    }
    $log=Join-Path $PSScriptRoot ('build-'+$target+'-'+$Attempt+'.log')
    & dotnet $ubt $target Win64 Development "-Project=$root/FPSGAME.uproject" -WaitMutex -NoHotReloadFromIDE -MaxParallelActions=4 "-log=$log"
    $code=$LASTEXITCODE
    @{target=$target;exit_code=$code;log=$log;finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot ('build-'+$target+'-'+$Attempt+'.json')) -Encoding utf8
    if($code -ne 0){exit $code}
}
