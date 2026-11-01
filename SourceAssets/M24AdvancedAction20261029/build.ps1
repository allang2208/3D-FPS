$ErrorActionPreference='Stop'
$m24Root='D:/FPS3D/FPSGAME'
$m24Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$m24Held=$false
try {
    Write-Output 'Waiting for existing UE batch.'
    try{$m24Held=$m24Gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$m24Held=$true}
    if(-not $m24Held){throw 'UE batch remains occupied.'}
    $m24Editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
    })
    if($m24Editors.Count){throw 'FPSGAME editor is running. Save and close it to build the new asset-authoring bridge. Existing editor retained.'}
    $m24Log=Join-Path $PSScriptRoot ('build-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$m24Root/FPSGAME.uproject" -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -ForceHeaderGeneration -NoUBA -MaxParallelActions=4 "-Log=$m24Log"
    if($LASTEXITCODE -ne 0){throw "Build failed: $LASTEXITCODE. See $m24Log"}
    @{complete=$true;published=$true;target='FPSGAMEEditor';completed=(Get-Date).ToString('o');log=$m24Log;runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build-receipt.json') -Encoding utf8
} finally {if($m24Held){$m24Gate.ReleaseMutex()};$m24Gate.Dispose()}
