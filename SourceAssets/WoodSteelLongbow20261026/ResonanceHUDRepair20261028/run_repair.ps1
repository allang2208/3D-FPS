$ErrorActionPreference='Stop'
$resonanceRoot='D:/FPS3D/FPSGAME'
$resonanceGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$resonanceHeld=$false
try {
    try {$resonanceHeld=$resonanceGate.WaitOne()} catch [Threading.AbandonedMutexException] {$resonanceHeld=$true}
    while($true) {
        $resonanceBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','UnrealEditor-Cmd.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $resonanceBusy.Count){break}
        Start-Sleep -Seconds 5
    }
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Preserve loaded packages; use the current editor bridge instead.'}
    $resonanceLog=Join-Path $PSScriptRoot 'repair-commandlet.log'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        ($resonanceRoot+'/FPSGAME.uproject') -run=pythonscript ('-script='+(Join-Path $PSScriptRoot 'repair_materials.py')) `
        -unattended -nop4 -nosplash -nosound -RenderOffscreen -AllowCommandletRendering -d3d12 `
        ('-abslog='+$resonanceLog) *> ($resonanceLog+'.stdout.txt')
    $resonanceCode=$LASTEXITCODE
    @{exit_code=$resonanceCode;finished=(Get-Date).ToString('s');game_started=$false} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $PSScriptRoot 'repair-commandlet.json') -Encoding utf8
    Get-Content -LiteralPath ($resonanceLog+'.stdout.txt') -Tail 12
    exit $resonanceCode
} finally {if($resonanceHeld){$resonanceGate.ReleaseMutex()};$resonanceGate.Dispose()}
