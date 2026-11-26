param([string]$Run='r1')
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
while(@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') }).Count){Start-Sleep -Seconds 5}
foreach($target in @('FPSGAMEEditor','FPSGAME')){
    if($target -eq 'FPSGAMEEditor'){
        while($true){try{$probe=[IO.File]::Open("$root/Binaries/Win64/UnrealEditor-FPSGAME.dll",'Open','ReadWrite','None');$probe.Dispose();break}catch [IO.IOException]{Start-Sleep -Seconds 5}}
    }
    $log="$root/Saved/Logs/UnknownLifeTravel20261116-$Run-$target"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development "-Project=$root/FPSGAME.uproject" -WaitMutex -NoHotReloadFromIDE -NoHotReload -NoUBA -NoUBALocal -NoXGE -NoSNDBS -NoFASTBuild -MaxParallelActions=4 "-Log=$log.log" *> "$log.console.log"
    Write-Output "$target exit=$LASTEXITCODE"
    if($LASTEXITCODE -ne 0){Get-Content -LiteralPath "$log.console.log" -Tail 35;exit $LASTEXITCODE}
}
