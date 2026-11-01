param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    for($attempt=0;$attempt -lt 20 -and -not $taskHeld;$attempt++) {
        try {$taskHeld=$taskGate.WaitOne([TimeSpan]::FromSeconds(30))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
        if(-not $taskHeld){Write-Output 'Waiting for existing UE batch.'}
    }
    if(-not $taskHeld){throw 'UE batch busy; nothing started.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE processes preserved; nothing started.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'}){throw 'Existing build preserved.'}
    if(-not $SkipBuild) {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "$taskRoot/FPSGAME.uproject" -NoHotReloadFromIDE *> (Join-Path $PSScriptRoot 'build.log')
        $code=$LASTEXITCODE
        @{exit_code=$code;target='FPSGAMEEditor Win64 Development'} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
        Write-Output "Build exit=$code"
        if($code -ne 0){Get-Content -LiteralPath (Join-Path $PSScriptRoot 'build.log') -Tail 55;exit $code}
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=WarhammerNetworkAudit -ConductiveGrips "-Out=$PSScriptRoot/audit.json" -unattended -nop4 -nosplash -NoSound -NoLiveCoding -NullRHI "-abslog=$PSScriptRoot/audit.log" *> (Join-Path $PSScriptRoot 'console.log')
    $code=$LASTEXITCODE
    Write-Output "Audit exit=$code"
    if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'audit.json')) {
        $report=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'audit.json') -Raw | ConvertFrom-Json
        $report | Select-Object count,failures,passed
        $report.checks | Where-Object {-not $_.passed}
    } else {Get-Content -LiteralPath (Join-Path $PSScriptRoot 'audit.log') -Tail 45}
    exit $code
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
