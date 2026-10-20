$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    Write-Output 'Waiting for the UE batch gate'
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(1200))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'UE batch gate remained busy; no build or asset writes started.'}
    $builds=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
    foreach($nativeBuild in $builds){
        $runningBuild=Get-Process -Id $nativeBuild.ProcessId -ErrorAction SilentlyContinue
        if($runningBuild){
            Write-Output "Waiting for native build process $($nativeBuild.ProcessId) to exit naturally"
            Wait-Process -InputObject $runningBuild -Timeout 1200
        }
    }
    foreach($ueProcess in @(Get-Process -Name UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue)) {
        $command=(Get-CimInstance Win32_Process -Filter "ProcessId=$($ueProcess.Id)").CommandLine
        if($command -and $command.Replace('\','/').IndexOf("$taskProject/FPSGAME.uproject",[StringComparison]::OrdinalIgnoreCase) -ge 0){
            if($ueProcess.ProcessName -eq 'UnrealEditor-Cmd'){
                Wait-Process -Id $ueProcess.Id -Timeout 60 -ErrorAction SilentlyContinue
                if(!(Get-Process -Id $ueProcess.Id -ErrorAction SilentlyContinue)){continue}
            }
            throw "Project modules are in use by PID $($ueProcess.Id); preserve it."
        }
    }
    Write-Output 'SVCH_REVIEW_BUILD_STARTED'
    foreach($target in @('FPSGAMEEditor','FPSGAME')) {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development "-Project=$taskProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$PSScriptRoot/build-$target.log" *> "$PSScriptRoot/build-$target-console.log"
        if($LASTEXITCODE -ne 0){throw "Build failed: $target"}
        Write-Output "SVCH_TARGET_BUILT $target"
    }
    @{complete=$true;targets=@('FPSGAMEEditor Win64 Development','FPSGAME Win64 Development');completed_utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build_receipt.json"
    Write-Output 'SVCH_REVIEW_BUILD_COMPLETE'
} catch {
    @{complete=$false;error=$_.Exception.Message;time_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath "$PSScriptRoot/build_error.json"
    throw
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
