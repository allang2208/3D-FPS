$ErrorActionPreference='Stop'
$inspectRoot='D:\FPS3D\FPSGAME'
$inspectScript=Join-Path $PSScriptRoot 'import_assets.py'
$inspectGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$inspectHeld=$false
try {
    $inspectHeld=$inspectGate.WaitOne([TimeSpan]::FromSeconds(300))
    if(-not $inspectHeld) { throw 'UE asset batch is still busy; no import sent.' }
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") {
        throw 'GUI editor appeared; preserve it and use the existing batch bridge.'
    }
    if(Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME') }) {
        throw 'Build or project commandlet is active; preserve it and defer the import.'
    }
    $inspectImportLog=Join-Path $PSScriptRoot 'import-commandlet.log'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' `
        (Join-Path $inspectRoot 'FPSGAME.uproject') '-run=pythonscript' ('-script='+$inspectScript) `
        -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        ('-abslog='+$inspectImportLog) -stdout -FullStdOutLogOutput *> (Join-Path $PSScriptRoot 'import-console.log')
    $inspectImportExit=$LASTEXITCODE
    @{exit_code=$inspectImportExit;log=$inspectImportLog;finished=(Get-Date).ToString('s')} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'import_commandlet_receipt.json') -Encoding utf8
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'import-console.log') -Tail 15
    exit $inspectImportExit
} finally {
    if($inspectHeld) {$inspectGate.ReleaseMutex()}
    $inspectGate.Dispose()
}
