$ErrorActionPreference='Stop'
$project='D:\FPS3D\FPSGAME'
$exe='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$oldSdk=$env:UE_SKIP_UBT_SDK_SETUP
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(10))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'UE batch still occupied; process preserved.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE session preserved.'}
    if(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'}){throw 'Existing build preserved.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $common=@("$project\FPSGAME.uproject",'-unattended','-nop4','-nosplash','-nullrhi','-nosound','-NoShaderCompile','-NoLiveCoding','-AssetGatherAll=false','-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False','-stdout','-FullStdOutLogOutput')
    & $exe @common '-run=KukriNetworkAudit' ("-Output="+(Join-Path $PSScriptRoot 'network-checks.json')) ("-abslog="+(Join-Path $PSScriptRoot 'network-engine.log')) *> (Join-Path $PSScriptRoot 'network-console.log')
    $netCode=$LASTEXITCODE
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'network-console.log') -Tail 5
    if($netCode -ne 0){exit $netCode}
    @{network_exit_code=$netCode;finished=(Get-Date).ToString('o');gui_started=$false;udp_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'checks-execution.json') -Encoding utf8
    exit $netCode
} finally {$env:UE_SKIP_UBT_SDK_SETUP=$oldSdk;if($held){$gate.ReleaseMutex()};$gate.Dispose()}
