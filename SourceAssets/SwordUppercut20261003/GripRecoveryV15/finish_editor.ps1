$ErrorActionPreference = 'Stop'
$uppercutRoot = 'D:\FPS3D\FPSGAME'
do {
    $uppercutBuilders = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('cl.exe','link.exe','UnrealBuildTool.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($uppercutBuilders.Count) {
        Wait-Process -Id $uppercutBuilders.ProcessId -Timeout 30 -ErrorAction SilentlyContinue
    }
} while ($uppercutBuilders.Count)
$uppercutEditors = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'UnrealEditor.exe' -and $_.CommandLine -match 'FPSGAME.uproject'
})
if ($uppercutEditors.Count) {
    Write-Output 'Applying uppercut camera changes through the existing editor Live Coding tool.'
    & "$uppercutRoot\Tools\AssetPipeline\mcp_call_codex.ps1" -Tool call_tool `
        -ArgumentsFile "$uppercutRoot\SourceAssets\SwordUppercut20261003\livecoding_request.json" `
        -OutputFile (Join-Path $PSScriptRoot 'livecoding_result_01.txt') -MaxOutputChars 2600 `
        -QueueWaitSeconds 180 -RequestTimeoutSeconds 1200
    exit $LASTEXITCODE
} else {
    & (Join-Path $PSScriptRoot 'build_uppercut.ps1') -Targets FPSGAMEEditor `
        *> (Join-Path $PSScriptRoot 'build_editor_console.log')
    exit $LASTEXITCODE
}
