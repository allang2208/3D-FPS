param([string[]]$Targets=@('FPSGAMEEditor','FPSGAME'),[string]$RecordsRoot='D:\FPS3D\FPSGAME\SourceAssets\HeQueBoss20261014\RigV01')
$ErrorActionPreference='Stop'
$hequeRoot=$RecordsRoot
$hequeBuild='E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat'
foreach($hequeTarget in $Targets) {
    $hequeWaiting=$false
    while($true) {
        $hequeBusy=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            $_.Name -eq 'cl.exe' -or $_.CommandLine -match 'UnrealBuildTool' -or ($hequeTarget -eq 'FPSGAMEEditor' -and $_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME.uproject')
        })
        if(-not $hequeBusy.Count){break}
        if(-not $hequeWaiting){Write-Output 'Waiting for the active build or commandlet.';$hequeWaiting=$true}
        Start-Sleep -Seconds 2
    }
    $hequeEditor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
    if($hequeTarget -eq 'FPSGAMEEditor' -and $hequeEditor.Count){throw 'The project editor is running; preserving its process and loaded assets.'}
    $hequeLog=Join-Path $hequeRoot ('Records/build-'+$hequeTarget+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    Write-Output "BUILD_STARTED $hequeTarget $hequeLog"
    & $hequeBuild $hequeTarget Win64 Development '-Project=D:\FPS3D\FPSGAME\FPSGAME.uproject' '-NoHotReloadFromIDE' *> $hequeLog
    $hequeCode=$LASTEXITCODE
    @{target=$hequeTarget;exit_code=$hequeCode;log=$hequeLog;finished=(Get-Date -Format o)}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $hequeRoot ('Records/build-'+$hequeTarget+'.json')) -Encoding utf8
    Write-Output "BUILD_FINISHED $hequeTarget EXIT=$hequeCode LOG=$hequeLog"
    if($hequeCode -ne 0){throw "Build failed: $hequeLog"}
}
