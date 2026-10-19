param([Parameter(Mandatory=$true)][string]$Step)
$ErrorActionPreference='Stop'
$drumRoot='D:/FPS3D/FPSGAME';$drumOut="$drumRoot/SourceAssets/Saiga12KInspectClearance20261018/Receipts"
$drumGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$drumHeld=$false
try {
 try {$drumHeld=$drumGate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$drumHeld=$true;throw 'Abandoned UE batch; preserve shared state.'}
 if(-not $drumHeld){throw 'Shared UE batch is still occupied; no commandlet started.'}
 if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Use existing editor through the MCP bridge; do not overwrite loaded assets.'}
 $env:UE_SKIP_UBT_SDK_SETUP='1'
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$drumRoot/FPSGAME.uproject" -run=pythonscript "-script=$drumRoot/Tools/Saiga12KInspectClearance/$Step.py" -NullRHI -unattended -nop4 -nosound -nosplash '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$drumOut/$Step.log" *> "$drumOut/$Step-console.log"
 $drumExit=$LASTEXITCODE
 @{step=$Step;exit_code=$drumExit;completed=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$drumOut/$Step-process.json" -Encoding utf8
 if($drumExit -ne 0){throw "$Step failed: $drumExit"}
} finally {if($drumHeld){$drumGate.ReleaseMutex()};$drumGate.Dispose()}
