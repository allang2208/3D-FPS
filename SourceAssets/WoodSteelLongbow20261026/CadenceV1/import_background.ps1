$ErrorActionPreference='Stop'
$cadenceProject='D:/FPS3D/FPSGAME'
$cadenceGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$cadenceHeld=$false
try {
    try {$cadenceHeld=$cadenceGate.WaitOne()} catch [Threading.AbandonedMutexException] {$cadenceHeld=$true}
    while($true) {
        $cadenceBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','UnrealEditor-Cmd.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $cadenceBusy.Count){break}
        Start-Sleep -Seconds 5
    }
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Editor is open; preserve its loaded packages and use the shared bridge.'}
    $cadenceLog=Join-Path $PSScriptRoot 'import-commandlet.log'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        ($cadenceProject+'/FPSGAME.uproject') -run=pythonscript ('-script='+(Join-Path $PSScriptRoot 'import_all.py')) `
        -unattended -nop4 -nosplash -nosound -nullrhi ('-abslog='+$cadenceLog) *> ($cadenceLog+'.stdout.txt')
    $cadenceResult=$LASTEXITCODE
    @{exit_code=$cadenceResult;finished=(Get-Date).ToString('s');game_run=$false} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $PSScriptRoot 'import-commandlet.json') -Encoding utf8
    Get-Content -LiteralPath ($cadenceLog+'.stdout.txt') -Tail 14
    exit $cadenceResult
} finally {if($cadenceHeld){$cadenceGate.ReleaseMutex()};$cadenceGate.Dispose()}
