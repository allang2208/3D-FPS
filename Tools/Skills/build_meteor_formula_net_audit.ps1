param([string[]]$Targets=@('FPSGAME','FPSGAMEEditor'),[switch]$ForceHeaderGeneration)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath 'D:\FPS3D\FPSGAME'
$taskDir='D:\FPS3D\FPSGAME\SourceAssets\MeteorFormulaNetAudit20261022'
foreach($target in $Targets){
    Write-Output "Waiting for build access: $target"
    while($true){
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool.dll') -or
            ($target -eq 'FPSGAMEEditor' -and $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME')
        })
        if($busy.Count -eq 0){break}
        Start-Sleep -Seconds 5
    }
    $attempt=1
    while(Test-Path -LiteralPath (Join-Path $taskDir "$target-build-$attempt.log")){$attempt++}
    $log=Join-Path $taskDir "$target-build-$attempt.log"
    $output=Join-Path $taskDir "$target-build-$attempt-output.log"
    $started=Get-Date
    $taskHeaderArgs=@()
    if($ForceHeaderGeneration){$taskHeaderArgs+='-ForceHeaderGeneration'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' $target Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 @taskHeaderArgs "-Log=$log" *> $output
    $code=$LASTEXITCODE
    [ordered]@{target=$target;exit_code=$code;started_at=$started.ToString('o');finished_at=(Get-Date).ToString('o');log=$log;runtime_tested=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $taskDir "$target-build-receipt.json") -Encoding utf8
    Get-Content -LiteralPath $output -Tail 14
    if($code -ne 0){exit $code}
}
