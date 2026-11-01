param([string]$Script='install.py',[switch]$WithRHI)
$ErrorActionPreference='Stop'
$opticRoot='D:/FPS3D/FPSGAME'
$opticGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$opticHeld=$false
try {
    try {$opticHeld=$opticGate.WaitOne([TimeSpan]::FromMinutes(15))}
    catch [Threading.AbandonedMutexException] {$opticHeld=$true}
    if(-not $opticHeld){throw 'UE asset batch remains occupied.'}
    $opticDeadline=(Get-Date).AddMinutes(30)
    while(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool'}) {
        if((Get-Date) -gt $opticDeadline){throw 'Existing build retained; asset launch deferred.'}
        Write-Output 'Waiting for the existing native build before loading its DLL.'
        Start-Sleep -Seconds 20
    }
    $opticExisting=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
    })
    if($opticExisting | Where-Object Name -eq 'UnrealEditor-Cmd.exe'){throw 'Existing asset process retained.'}
    $opticStamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    if($opticExisting | Where-Object Name -eq 'UnrealEditor.exe') {
        & "$opticRoot/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$PSScriptRoot/$Script" -QueueWaitSeconds 60 -RequestTimeoutSeconds 240 -OutputFile "$PSScriptRoot/$Script-$opticStamp.json" -MaxOutputChars 1800
    } else {
        $opticRHI=if($WithRHI){@('-AllowCommandletRendering','-RenderOffscreen')}else{@('-nullrhi')}
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$opticRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended -nop4 -nosplash -nosound @opticRHI "-abslog=$PSScriptRoot/$Script-$opticStamp.log" *> "$PSScriptRoot/$Script-$opticStamp.stdout.txt"
    }
    if($LASTEXITCODE -ne 0){throw "Scope asset step failed: $Script"}
    Write-Output "Scope asset step finished: $Script"
} finally {if($opticHeld){$opticGate.ReleaseMutex()};$opticGate.Dispose()}
