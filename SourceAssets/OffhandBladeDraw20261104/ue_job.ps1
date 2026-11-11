param([Parameter(Mandatory=$true)][ValidateSet('author')][string]$Job)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$script=Join-Path $PSScriptRoot ($Job+'.py')
$deadline=(Get-Date).AddMinutes(20)
while ((Get-Date) -lt $deadline) {
    if(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME') -or ($_.Name -in @('dotnet.exe','UnrealBuildTool.exe') -and $_.CommandLine -match 'UnrealBuildTool' -and $_.CommandLine -match 'FPSGAMEEditor')}){Start-Sleep -Seconds 5;continue}
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object CommandLine -match 'FPSGAME'){
        & "$root/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $script -QueueWaitSeconds 90 -RequestTimeoutSeconds 300 -OutputFile "$PSScriptRoot/$Job-bridge.txt" -MaxOutputChars 1000
        if($LASTEXITCODE -eq 75){continue}
        if($LASTEXITCODE -eq 3 -and -not(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object CommandLine -match 'FPSGAME')){continue}
        exit $LASTEXITCODE
    }
    $gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
    try{
        $held=$gate.WaitOne([TimeSpan]::FromSeconds(30));if(!$held){continue}
        if(Get-CimInstance Win32_Process|Where-Object {$_.Name -like 'UnrealEditor*' -and $_.CommandLine -match 'FPSGAME'}){continue}
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$root/FPSGAME.uproject" -run=pythonscript "-script=$script" -unattended -nop4 -nosplash -NullRHI -nosound "-abslog=$PSScriptRoot/$Job.log" *> "$PSScriptRoot/$Job-console.log"
        exit $LASTEXITCODE
    }finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
}
throw 'UE asset batch is occupied'
