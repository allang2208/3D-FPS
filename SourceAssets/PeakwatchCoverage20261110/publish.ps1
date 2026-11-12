$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$deadline=(Get-Date).AddMinutes(15)
try {
    while(-not $held){
        try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(30))}
        catch [Threading.AbandonedMutexException] {$held=$true}
        if((Get-Date) -gt $deadline){throw 'UE asset batch is still occupied; no write sent.'}
    }
    while($true){
        $jobs=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $jobs.Count){break}
        if((Get-Date) -gt $deadline){throw 'Existing engine process retained; publication deferred.'}
        Start-Sleep -Seconds 10
    }
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Editor is open; use the existing asset bridge.'}
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $log="$PSScriptRoot/assets-$stamp.log";$stdout="$PSScriptRoot/assets-$stamp.stdout.txt"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" `
        -run=pythonscript "-script=$PSScriptRoot/publish_coverage.py" -unattended -nop4 -nosound -nosplash `
        -AllowCommandletRendering -RenderOffscreen '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$log" *> $stdout
    $code=$LASTEXITCODE
    [ordered]@{exit_code=$code;log=$log;stdout=$stdout;runtime_tested=$false} |
        ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/commandlet-result.json" -Encoding utf8
    if($code -ne 0){throw "Coverage publication exited $code; see $log"}
    Write-Output 'Peakwatch coverage material saved; gameplay testing remains manual.'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
