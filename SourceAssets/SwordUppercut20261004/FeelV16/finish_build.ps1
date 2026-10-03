$ErrorActionPreference = 'Stop'
$uppercutRoot = 'D:\FPS3D\FPSGAME'
function Wait-UppercutBuildWindow {
    do {
        $uppercutBuilders = @(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('cl.exe','link.exe','UnrealBuildTool.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if ($uppercutBuilders.Count) {
            Wait-Process -Id $uppercutBuilders.ProcessId -Timeout 30 -ErrorAction SilentlyContinue
        }
    } while ($uppercutBuilders.Count)
}
Wait-UppercutBuildWindow
Write-Output 'Building uppercut V16 Game target.'
& (Join-Path $PSScriptRoot 'build_uppercut.ps1') -Targets FPSGAME `
    *> (Join-Path $PSScriptRoot 'build_game_console.log')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Wait-UppercutBuildWindow
$uppercutEditors = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME.uproject'
})
if ($uppercutEditors.Count) {
    Write-Output 'Applying uppercut V16 through the existing editor Live Coding tool.'
    & "$uppercutRoot\Tools\AssetPipeline\mcp_call_codex.ps1" -Tool call_tool `
        -ArgumentsFile (Join-Path $PSScriptRoot 'livecoding_request.json') `
        -OutputFile (Join-Path $PSScriptRoot 'livecoding_result_01.txt') -MaxOutputChars 2600 `
        -QueueWaitSeconds 180 -RequestTimeoutSeconds 1200
    exit $LASTEXITCODE
} else {
    Write-Output 'Building uppercut V16 Editor target in the background.'
    & (Join-Path $PSScriptRoot 'build_uppercut.ps1') -Targets FPSGAMEEditor `
        *> (Join-Path $PSScriptRoot 'build_editor_console.log')
    exit $LASTEXITCODE
}
