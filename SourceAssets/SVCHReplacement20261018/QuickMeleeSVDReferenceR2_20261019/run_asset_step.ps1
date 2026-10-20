param([Parameter(Mandatory=$true)][string]$ScriptName,[Parameter(Mandatory=$true)][string]$LogStem)
$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    Write-Output 'Waiting for UE asset batch gate'
    try{$held=$gate.WaitOne([TimeSpan]::FromSeconds(1200))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(!$held){throw 'UE batch window remained occupied'}
    foreach($p in @(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe')})){
        if($p.CommandLine -and $p.CommandLine.Replace('\','/').Contains('D:/FPS3D/FPSGAME')){
            if($p.Name -eq 'UnrealEditor-Cmd.exe'){
                Wait-Process -Id $p.ProcessId -Timeout 60 -ErrorAction SilentlyContinue
                if(!(Get-Process -Id $p.ProcessId -ErrorAction SilentlyContinue)){continue}
            }
            throw "Preserve running UE process $($p.ProcessId)"
        }
    }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    Write-Output "SVCH_ASSET_STEP_STARTED $ScriptName"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$PSScriptRoot/$ScriptName" -unattended -nosplash -nosound -NullRHI "-abslog=$PSScriptRoot/$LogStem.log" *> "$PSScriptRoot/$LogStem-console.log"
    if($LASTEXITCODE -ne 0){throw "Asset step failed: $ScriptName"}
    Write-Output "SVCH_ASSET_STEP_COMPLETE $ScriptName"
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
