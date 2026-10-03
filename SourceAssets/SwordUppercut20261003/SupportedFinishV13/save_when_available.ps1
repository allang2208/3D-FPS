$ErrorActionPreference = 'Stop'
$uppercutProject = 'D:\FPS3D\FPSGAME'
$uppercutScript = Join-Path $PSScriptRoot 'install_uppercut_v13.py'
do {
    $uppercutBuilders = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealBuildTool.exe$|^cl.exe$|^link.exe$' -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($uppercutBuilders.Count) {
        Wait-Process -Id $uppercutBuilders.ProcessId -Timeout 30 -ErrorAction SilentlyContinue
    }
} while ($uppercutBuilders.Count)
$uppercutEditors = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'UnrealEditor.exe' -and
    ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')
})
if ($uppercutEditors.Count) {
    & "$uppercutProject\Tools\AssetPipeline\mcp_call_codex.ps1" -PythonScript $uppercutScript -OutputFile (Join-Path $PSScriptRoot 'install_bridge_02.txt') -MaxOutputChars 2200 -QueueWaitSeconds 180 -RequestTimeoutSeconds 180
    exit $LASTEXITCODE
}
$uppercutConflict = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'SwordUppercut20261003'
})
if ($uppercutConflict.Count) { throw 'Another uppercut commandlet is active; preserving the animation packages.' }
& 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$uppercutProject\FPSGAME.uproject" -run=pythonscript "-script=$uppercutScript" -unattended -nop4 -nosplash -nullrhi -nosound -stdout -FullStdOutLogOutput "-abslog=$PSScriptRoot\install_commandlet.log" *> "$PSScriptRoot\install_commandlet_console.log"
exit $LASTEXITCODE
