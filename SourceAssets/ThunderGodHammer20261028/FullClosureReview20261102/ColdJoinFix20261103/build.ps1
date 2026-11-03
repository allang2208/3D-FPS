$ErrorActionPreference='Stop'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$project='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied; no build started.'}
    $deadline=(Get-Date).AddMinutes(20)
    while(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    }){
        if((Get-Date) -gt $deadline){throw 'Editor/build remained active; nothing was stopped.'}
        Start-Sleep -Seconds 5
    }
    $sources=@(Get-ChildItem -LiteralPath "$PSScriptRoot/Before" -File | ForEach-Object {
        $p="$project/Source/FPSGAME/Characters/$($_.Name)"
        @{path=$p;sha256=(Get-FileHash -LiteralPath $p).Hash}
    })
    $sources|ConvertTo-Json|Set-Content -LiteralPath "$PSScriptRoot/build-source-inputs.json" -Encoding utf8
    foreach($target in @('FPSGAMEEditor','FPSGAME')){
        $flags=@()
        $defs="$project/Intermediate/Build/Win64/x64/FPSGAMEEditor/Development/UnrealEd/SharedDefinitions.UnrealEd.Project.ValApi.ValExpApi.Cpp20.h"
        if($target -eq 'FPSGAMEEditor' -and (Test-Path -LiteralPath $defs) -and (Select-String -LiteralPath $defs -Pattern '^#define WITH_LIVE_CODING 0$' -Quiet)){$flags+='-NoLiveCoding'}
        Write-Output "COLD_JOIN_BUILD_START $target"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development "-Project=$project/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 @flags "-Log=$PSScriptRoot/$target-build.log" *> "$PSScriptRoot/$target-console.log"
        $code=$LASTEXITCODE
        @{target=$target;exit_code=$code;completed=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath "$PSScriptRoot/$target-receipt.json" -Encoding utf8
        if($code -ne 0){throw "$target build failed; see its console log."}
        Write-Output "COLD_JOIN_BUILD_DONE $target"
    }
    $outputs=@('UnrealEditor-FPSGAME.dll','FPSGAME.exe')|ForEach-Object {
        $p="$project/Binaries/Win64/$_"
        @{path=$p;sha256=(Get-FileHash -LiteralPath $p).Hash;bytes=(Get-Item -LiteralPath $p).Length}
    }
    $unchanged=-not @($sources|Where-Object {(Get-FileHash -LiteralPath $_.path).Hash -ne $_.sha256}).Count
    @{compiled=$true;owned_sources_unchanged_during_build=$unchanged;outputs=$outputs;runtime_tested=$false;editor_launched=$false;completed=(Get-Date).ToString('o')}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath "$PSScriptRoot/build-receipt.json" -Encoding utf8
    Write-Output "COLD_JOIN_BUILD_READY sources_unchanged=$unchanged"
} finally {
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
