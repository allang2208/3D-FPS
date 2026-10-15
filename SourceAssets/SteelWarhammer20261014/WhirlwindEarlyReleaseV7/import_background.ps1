$ErrorActionPreference='Stop'
$whirlwindRoot='D:\FPS3D\FPSGAME'
$whirlwindScript=Join-Path $PSScriptRoot 'import_assets.py'
$whirlwindGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$whirlwindHeld=$false
try {
    $whirlwindHeld=$whirlwindGate.WaitOne([TimeSpan]::FromSeconds(300))
    if(-not $whirlwindHeld) { throw 'UE asset batch is still busy; no import sent.' }
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") {
        throw 'GUI editor appeared; preserve it and use the existing batch bridge.'
    }
    if(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME') }) {
        throw 'Build or project commandlet is active; preserve it and defer the import.'
    }
    $whirlwindImportLog=Join-Path $PSScriptRoot 'import-commandlet.log'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
        (Join-Path $whirlwindRoot 'FPSGAME.uproject') '-run=pythonscript' ('-script='+$whirlwindScript) `
        -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        ('-abslog='+$whirlwindImportLog) -stdout -FullStdOutLogOutput *> (Join-Path $PSScriptRoot 'import-console.log')
    $whirlwindImportExit=$LASTEXITCODE
    @{exit_code=$whirlwindImportExit;log=$whirlwindImportLog;finished=(Get-Date).ToString('s')} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'import_commandlet_receipt.json') -Encoding utf8
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'import-console.log') -Tail 15
    exit $whirlwindImportExit
} finally {
    if($whirlwindHeld) {$whirlwindGate.ReleaseMutex()}
    $whirlwindGate.Dispose()
}
