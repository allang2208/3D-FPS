$ErrorActionPreference='Stop'
$opticRoot='D:/FPS3D/FPSGAME'
$opticGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$opticHeld=$false
try {
    try {$opticHeld=$opticGate.WaitOne([TimeSpan]::FromMinutes(30))}
    catch [Threading.AbandonedMutexException] {$opticHeld=$true}
    if(-not $opticHeld){throw 'Existing UE batch retained.'}
    $opticDeadline=(Get-Date).AddMinutes(30)
    while(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -match 'UnrealBuildTool'}) {
        if((Get-Date) -gt $opticDeadline){throw 'Existing build retained; no overlapping build submitted.'}
        Write-Output 'Waiting for the existing native build.'
        Start-Sleep -Seconds 20
    }
    $opticEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
    })
    if($opticEditors.Count){throw 'Existing editor/asset process retained; normal DLL link deferred.'}
    $opticLog=Join-Path $PSScriptRoot ('build-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$opticRoot/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -NoUBA -MaxParallelActions=4 "-Log=$opticLog"
    if($LASTEXITCODE -ne 0){throw "Build failed: $LASTEXITCODE. $opticLog"}
    @{target='FPSGAMEEditor';exit_code=0;published=$true;runtime_tested=$false;log=$opticLog;completed=(Get-Date).ToString('o')} |
        ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot 'build-receipt.json') -Encoding utf8
    Write-Output 'Shared physical optics built and saved; no editor or game launched.'
} finally {if($opticHeld){$opticGate.ReleaseMutex()};$opticGate.Dispose()}
