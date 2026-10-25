$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$sdkBefore=$env:UE_SKIP_UBT_SDK_SETUP
try {
    while(-not $held){try{$held=$gate.WaitOne(30000)}catch [Threading.AbandonedMutexException]{$held=$true}}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Preserving the running editor; isolated native audit needs the project DLL available.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' `
        -run=WarhammerNetworkAudit -SprintOnly ('-Out='+ (Join-Path $PSScriptRoot 'authority.json')) `
        -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile ('-abslog='+ (Join-Path $PSScriptRoot 'authority-engine.log')) `
        -stdout -FullStdOutLogOutput *> (Join-Path $PSScriptRoot 'authority-console.log')
    $result=$LASTEXITCODE
    @{exit_code=$result;finished=(Get-Date).ToString('s')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'authority-receipt.json') -Encoding utf8
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'authority-console.log') -Tail 16
    exit $result
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$sdkBefore
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
