$ErrorActionPreference='Stop'
$bowImpactProject='D:/FPS3D/FPSGAME'
$bowImpactScript=Join-Path $PSScriptRoot 'import_impact.py'
if(Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue){
    & "$bowImpactProject/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $bowImpactScript `
        -OutputFile (Join-Path $PSScriptRoot ('import-bridge-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.txt')) -MaxOutputChars 3000
    exit $LASTEXITCODE
}
$bowImpactGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$bowImpactHeld=$false
try {
    try {$bowImpactHeld=$bowImpactGate.WaitOne([TimeSpan]::FromHours(1))} catch [Threading.AbandonedMutexException] {$bowImpactHeld=$true}
    if(-not $bowImpactHeld){throw 'Asset batch busy; import not started.'}
    while(@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        $_.Name -eq 'UnrealBuildTool.exe' -or $_.Name -eq 'UnrealEditor-Cmd.exe' -or
        ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build\.bat')
    }).Count){Start-Sleep -Seconds 5}
    if(Get-Process -Name UnrealEditor,FPSGAME -ErrorAction SilentlyContinue){
        Write-Output 'Editor/game opened while waiting; preserve it. No commandlet started.'
        exit 75
    }
    $bowImpactLog=Join-Path $PSScriptRoot 'import-console.log'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$bowImpactProject/FPSGAME.uproject" -run=pythonscript "-script=$bowImpactScript" `
        -unattended -nop4 -NullRHI -nosound -nosplash -UTF8Output `
        ('-abslog='+(Join-Path $PSScriptRoot 'import-engine.log')) *> $bowImpactLog
    $bowImpactExit=$LASTEXITCODE
    Get-Content -LiteralPath $bowImpactLog -Tail 12
    if($bowImpactExit -ne 0){exit $bowImpactExit}
    if(-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'import-receipt.json'))){throw 'Import returned without a save receipt.'}
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'import-receipt.json')
} finally {if($bowImpactHeld){$bowImpactGate.ReleaseMutex()};$bowImpactGate.Dispose()}
