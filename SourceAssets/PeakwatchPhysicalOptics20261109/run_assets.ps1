param([string]$Script='publish_assets.py')
$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(60))}
    catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'UE asset batch remains busy; no write was sent.'}
    $build=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'UnrealBuildTool.exe'
    })
    if($build.Count){throw 'Existing native build retained; run after it completes.'}
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
    })
    if($editors.Count){throw 'Existing editor retained; use its asset bridge instead.'}
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $engineLog="$PSScriptRoot/assets-$stamp.log"
    $stdout="$PSScriptRoot/assets-$stamp.stdout.txt"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" `
        -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended -nop4 -nosplash -nosound `
        -AllowCommandletRendering -RenderOffscreen '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$engineLog" *> $stdout
    $code=$LASTEXITCODE
    [ordered]@{exit_code=$code;log=$engineLog;stdout=$stdout;runtime_tested=$false} |
        ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/$Script-result.json" -Encoding utf8
    if($code -ne 0){throw "Asset commandlet exited $code; see $engineLog"}
    Write-Output "Peakwatch assets saved: $engineLog"
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
