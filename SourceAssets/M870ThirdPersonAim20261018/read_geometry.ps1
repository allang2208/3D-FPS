$ErrorActionPreference='Stop'
$m870Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$m870Held=$false
$m870SdkSetting=$env:UE_SKIP_UBT_SDK_SETUP
try {
    $m870Held=$m870Gate.WaitOne([TimeSpan]::FromMinutes(15))
    if(-not $m870Held){throw 'UE asset batch remained busy; no operation sent.'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript ('-script='+(Join-Path $PSScriptRoot 'read_geometry.py')) `
        -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        ('-abslog='+(Join-Path $PSScriptRoot 'read-engine.log')) -stdout -FullStdOutLogOutput *> (Join-Path $PSScriptRoot 'read-console.log')
    $m870Exit=$LASTEXITCODE
    @{exit_code=$m870Exit;finished=(Get-Date).ToString('s');asset_writes=$false} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot 'read-receipt.json') -Encoding utf8
    Get-Content (Join-Path $PSScriptRoot 'read-console.log') -Tail 8
    exit $m870Exit
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP=$m870SdkSetting
    if($m870Held){$m870Gate.ReleaseMutex()};$m870Gate.Dispose()
}
