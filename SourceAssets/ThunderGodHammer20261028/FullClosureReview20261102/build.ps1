param([switch]$WithGame)
$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'Existing UE batch busy; no build started.'}
    $deadline=(Get-Date).AddMinutes(20)
    do {
        $busy=@(Get-CimInstance Win32_Process | Where-Object { ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and $_.ThreadCount -gt 0) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
        if(-not $busy.Count){break}
        if((Get-Date) -gt $deadline){throw 'Editor or build remained active. No process was stopped.'}
        Start-Sleep -Seconds 5
    }while($true)
    $targets=@('FPSGAMEEditor');if($WithGame){$targets+='FPSGAME'}
    foreach($target in $targets){
        $liveCodingFlags=@()
        $definitions='D:/FPS3D/FPSGAME/Intermediate/Build/Win64/x64/FPSGAMEEditor/Development/UnrealEd/SharedDefinitions.UnrealEd.Project.ValApi.ValExpApi.Cpp20.h'
        if($target -eq 'FPSGAMEEditor' -and (Test-Path $definitions) -and (Select-String -LiteralPath $definitions -Pattern '^#define WITH_LIVE_CODING 0$' -Quiet)){$liveCodingFlags+='-NoLiveCoding'}
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -MaxParallelActions=4 @liveCodingFlags "-Log=$PSScriptRoot/production-$target.log" *> "$PSScriptRoot/production-$target-console.log"
        @{target=$target;exit_code=$LASTEXITCODE;completed=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content "$PSScriptRoot/build-$target.json" -Encoding utf8
        if($LASTEXITCODE -ne 0){throw "$target build failed"}
    }
    $from='D:/FPS3D/FPSGAME/Binaries/Win64';$to='D:/FPS3D/ThunderHammerFullReviewHost20261102/Binaries/Win64'
    foreach($name in @('UnrealEditor-FPSGAME.dll','UnrealEditor.modules','FPSGAMEEditor.target')){Copy-Item -LiteralPath "$from/$name" -Destination "$to/$name" -Force}
    @{runtime_host=$to;dll_sha256=(Get-FileHash "$to/UnrealEditor-FPSGAME.dll").Hash;source_project='D:/FPS3D/FPSGAME';completed=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content "$PSScriptRoot/runtime-build.json" -Encoding utf8
    Write-Output 'THUNDER_CLOSURE_BUILD_READY'
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
