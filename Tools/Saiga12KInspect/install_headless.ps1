$ErrorActionPreference='Stop'
$inspectRoot='D:/FPS3D/FPSGAME'
$inspectOut="$inspectRoot/SourceAssets/Saiga12KInspect20261018/Receipts"
# Use the existing MCP batch mutex and the current project.
# Refuse a live editor; use its bridge instead of overwriting loaded assets.
$inspectGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$inspectHeld=$false
try {
 try {$inspectHeld=$inspectGate.WaitOne([TimeSpan]::FromMinutes(10))}
 catch [Threading.AbandonedMutexException] {$inspectHeld=$true;throw 'Abandoned UE batch: preserve state; installation was not started.'}
 if(-not $inspectHeld){throw 'UE batch wait expired; installation was not started.'}
 if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Editor reopened; preserve its active state.'}
 $env:UE_SKIP_UBT_SDK_SETUP='1'
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$inspectRoot/FPSGAME.uproject" -run=pythonscript "-script=$inspectRoot/Tools/Saiga12KInspect/install_profiles.py" -NullRHI -unattended -nop4 -nosound -nosplash '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$inspectOut/install-headless.log" *> "$inspectOut/install-headless-console.log"
 if($LASTEXITCODE -ne 0){throw "Profile installation failed: $LASTEXITCODE"}
} finally {
 if($inspectHeld){$inspectGate.ReleaseMutex()}
 $inspectGate.Dispose()
}
