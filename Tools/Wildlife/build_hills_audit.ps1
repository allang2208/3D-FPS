param([string[]]$Targets=@('FPSGAME','FPSGAMEEditor'))
$ErrorActionPreference='Stop'
$auditProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$auditDir=Join-Path $auditProject 'Saved/HillsMultiplayerClosure20261115'
New-Item -ItemType Directory -Force -Path (Join-Path $auditDir 'Logs') | Out-Null
$auditGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$auditHeld=$false
try {
    try {$auditHeld=$auditGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$auditHeld=$true}
    if(-not $auditHeld){throw 'Build queue timeout'}
    foreach($target in $Targets){
        $deadline=[DateTime]::UtcNow.AddMinutes(10)
        while($true){
            $busy=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'})
            if(-not $busy.Count){break}
            if([DateTime]::UtcNow -gt $deadline){throw 'Another native build is still running'}
            Start-Sleep -Seconds 5
        }
        $binary=if($target -eq 'FPSGAMEEditor'){'UnrealEditor-FPSGAME.dll'}else{'FPSGAME.exe'}
        if(Test-Path -LiteralPath "$auditProject/Binaries/Win64/$binary"){
            $probe=[IO.File]::Open("$auditProject/Binaries/Win64/$binary",[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None);$probe.Dispose()
        }
        $log="$auditDir/Logs/native-$target.log"
        Write-Output "AUDIT_BUILD_START $target"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $target Win64 Development "-Project=$auditProject/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -UBA -UBADisableRemote -MaxParallelActions=2 "-UBARootDir=$auditDir/UbaCache" -UBAStoreCapacityGb=4 "-Log=$log" *> "$auditDir/Logs/native-$target-stdout.log"
        $code=$LASTEXITCODE
        @{target=$target;exit_code=$code;log=$log;completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$auditDir/build-$target.json" -Encoding utf8
        Write-Output "AUDIT_BUILD_END $target exit=$code"
        if($code -ne 0){throw "Build failed: $log"}
    }
} finally {if($auditHeld){$auditGate.ReleaseMutex()};$auditGate.Dispose()}
