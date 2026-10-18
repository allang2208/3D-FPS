param([string]$Script='read_inputs.py')
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    while(-not $held){
        try {$held=$gate.WaitOne(45000)} catch [Threading.AbandonedMutexException] {$held=$true}
        if(-not $held){Write-Output 'Waiting for the existing UE batch.'}
    }
    while($true){
        if(Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue){throw 'GUI editor is open; preserve it.'}
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealEditor-Cmd.exe' -or
            ($_.Name -in @('dotnet.exe','UnrealBuildTool.exe') -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor')})
        if(-not $busy.Count){break}
        Write-Output 'Waiting for the existing commandlet or Editor build.'
        try {Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop}
        catch [System.TimeoutException]{} catch {if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $priorSkip=$env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended -nop4 -nosplash -nosound -nullrhi "-abslog=$PSScriptRoot/commandlet-$stamp.log" *> "$PSScriptRoot/console-$stamp.log"
        if($LASTEXITCODE -ne 0){throw "Commandlet failed; see console-$stamp.log"}
        Write-Output "M870_ROOT_COMMANDLET_COMPLETE console-$stamp.log"
    } finally {$env:UE_SKIP_UBT_SDK_SETUP=$priorSkip}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
