$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME/SourceAssets/Super90AttachmentAudit20261016'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $deadline=[DateTime]::UtcNow.AddMinutes(45)
    while([DateTime]::UtcNow -lt $deadline){
        $building=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='UnrealBuildTool.exe'") | Where-Object {$_.CommandLine -match 'UnrealBuildTool'}
        if($building){
            $observedBuild=Get-Process -Id $building[0].ProcessId -ErrorAction SilentlyContinue
            if($observedBuild){[void]$observedBuild.WaitForExit(10000)}
            continue
        }
        try{$held=$gate.WaitOne(1000)}catch [Threading.AbandonedMutexException]{$held=$true}
        if(-not $held){continue}
        $running=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'") | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject'}
        if(-not $running){break}
        $gate.ReleaseMutex();$held=$false

        $observedCommandlet=Get-Process -Id $running[0].ProcessId -ErrorAction SilentlyContinue
        if($observedCommandlet){[void]$observedCommandlet.WaitForExit(10000)}
    }
    if(-not $held){Write-Output 'BUILD_WINDOW_STILL_BUSY';exit 75}
    foreach($target in @('FPSGAMEEditor','FPSGAME')){
        $started=[DateTime]::UtcNow.ToString('o')
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$taskRoot/build_$target.log"
        $resultCode=$LASTEXITCODE
        @{target="$target Win64 Development";exitCode=$resultCode;startedUtc=$started;finishedUtc=[DateTime]::UtcNow.ToString('o');runtimeTested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/build_${target}_receipt.json" -Encoding utf8
        if($resultCode -ne 0){exit $resultCode}
    }
    exit 0
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
