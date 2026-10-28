$ErrorActionPreference='Stop'
$taskProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$taskDeadline=(Get-Date).AddMinutes(10)
do {
$taskBusy=@(Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -match '^UnrealEditor.*\.exe$' -and $_.CommandLine -and $_.CommandLine.Replace('/','\').Contains($taskProject)) -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'FPSGAME.exe')
})
if(!$taskBusy.Count){break}
if((Get-Date) -ge $taskDeadline){throw 'The project is in use; keep the isolated audit pending.'}
Write-Output ('Waiting for module users: '+(($taskBusy | ForEach-Object {$_.ProcessId}) -join ','))
Wait-Process -Id $taskBusy.ProcessId -Timeout 45 -ErrorAction SilentlyContinue
} while($true)
$taskOutput=Join-Path $PSScriptRoot 'audit-result.json'
$taskLog=Join-Path $PSScriptRoot 'audit.log'
$taskPreviousSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $taskProject -run=KukriNetworkAudit "-Output=$taskOutput" "-abslog=$taskLog" -unattended -nosplash -nullrhi -nosound -NoLiveCoding *> (Join-Path $PSScriptRoot 'audit-console.log')
    $taskExit=$LASTEXITCODE
    if(Test-Path -LiteralPath $taskOutput){Get-Content -LiteralPath $taskOutput}
    else {Get-Content -LiteralPath $taskLog -Tail 18}
    exit $taskExit
} finally {$env:UE_SKIP_UBT_SDK_SETUP=$taskPreviousSdk}
