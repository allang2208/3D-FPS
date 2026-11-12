param([string]$Script='collect.py')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'UE batch wait expired'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
    if($busy.Count){throw 'Existing build or commandlet retained'}
    $stamp=Get-Date -Format 'yyyyMMdd_HHmmssfff'
    if(@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'").Count){
        & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$PSScriptRoot/$Script" -OutputFile "$PSScriptRoot/$Script.$stamp.bridge.txt" -MaxOutputChars 3000
        if(!$?){throw 'Editor Python batch failed'}
    }else{
        $log="$PSScriptRoot/$Script.$stamp.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended -NullRHI -NoSound -NoP4 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$log" *> "$log.console"
        $code=$LASTEXITCODE
        Get-Content -LiteralPath $log -Tail 8
        if($code -ne 0){throw "Wrist33 commandlet exit $code"}
    }
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
