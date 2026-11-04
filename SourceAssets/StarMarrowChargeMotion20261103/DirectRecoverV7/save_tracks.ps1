param([Parameter(Mandatory=$true)][string]$Script)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
function Test-TaskProject($Process) {
    if([string]::IsNullOrWhiteSpace($Process.CommandLine)){return $true}
    return $Process.CommandLine.Replace('\','/') -match '(?i)(?:^|[\s"])(?:D:/FPS3D/FPSGAME/)?FPSGAME\.uproject(?=[\s"]|$)'
}
$taskStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$taskName=[IO.Path]::GetFileNameWithoutExtension($Script)
$taskScript=Join-Path $PSScriptRoot $Script
$taskEditors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {Test-TaskProject $_})
if($taskEditors.Count -gt 0){
    & "$taskRoot/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $taskScript -OutputFile "$PSScriptRoot/$taskName-response-$taskStamp.json" -MaxOutputChars 2800 -QueueWaitSeconds 300 -RequestTimeoutSeconds 240
    if($LASTEXITCODE -ne 0){throw 'Current editor operation did not complete; preserve it.'}
} else {
    $taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
    try {
        while(-not $taskHeld){
            try{$taskHeld=$taskGate.WaitOne(10000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
            if(-not $taskHeld){continue}
            $taskCommandlets=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object {Test-TaskProject $_})
            if($taskCommandlets.Count -gt 0){$taskGate.ReleaseMutex();$taskHeld=$false;Start-Sleep -Seconds 10}
        }
        $taskRunning=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {Test-TaskProject $_})
        if($taskRunning.Count -gt 0){throw 'An FPSGAME process appeared; preserve it and use the shared bridge.'}
        $taskLog="$PSScriptRoot/$taskName-$taskStamp.log"
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -unattended -nop4 -nosplash -nosound -Multiprocess -nullrhi '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$taskLog" *> "$PSScriptRoot/$taskName-$taskStamp.console.log"
        $taskExit=$LASTEXITCODE
        $taskOutput=Get-Content -LiteralPath $taskLog -Raw -Encoding UTF8
        $taskComplete=$taskOutput -match 'Python script executed successfully' -and $taskOutput -match 'Success - 0 error\(s\)'
        @{exit_code=$taskExit;script_complete=$taskComplete;log=$taskLog} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/$taskName-process.json" -Encoding utf8
        if($taskExit -ne 0 -and -not ($taskExit -eq 1 -and $taskComplete)){throw "Charge animation asset task failed; read $taskLog"}
        Write-Output "CHARGE_ANIMATION_ASSET_TASK_COMPLETE $taskName $taskLog"
    } finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
}
