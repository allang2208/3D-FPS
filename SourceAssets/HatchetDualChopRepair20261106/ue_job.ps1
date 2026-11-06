param([Parameter(Mandatory=$true)][string]$Job)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME'
$taskScript=Join-Path $PSScriptRoot ($Job+'.py')
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskOldSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try{$taskHeld=$taskGate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$taskHeld=$true}
    if(-not $taskHeld){throw 'UE batch is occupied.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Existing editor retained; use its asset bridge for this batch.'}
    $taskBuilds=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'})
    foreach($proc in $taskBuilds){try{[Diagnostics.Process]::GetProcessById($proc.ProcessId).WaitForExit()}catch [ArgumentException]{}}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskScript" -unattended -nop4 -nosplash -NullRHI -nosound '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$PSScriptRoot/$Job.log" *> "$PSScriptRoot/$Job-console.log"
    if($LASTEXITCODE -ne 0){throw "Asset batch failed: $Job"}
    Write-Output "Asset batch completed: $Job"
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$taskOldSdk
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
