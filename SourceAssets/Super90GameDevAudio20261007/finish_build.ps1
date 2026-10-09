$ErrorActionPreference = 'Stop'
$projectRoot = 'D:/FPS3D/FPSGAME'
$outputRoot = "$projectRoot/SourceAssets/Super90GameDevAudio20261007"
Write-Output 'Waiting for the current native build to release UBT.'
do {
    $busy = @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('cl.exe', 'link.exe', 'UnrealEditor-Cmd.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if ($busy.Count -gt 0) { Start-Sleep -Seconds 10 }
} while ($busy.Count -gt 0)
$editor = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'")
if ($editor.Count -gt 0) {
    Write-Output 'Compiling the audio routing in the existing editor.'
    & "$projectRoot/Tools/AssetPipeline/mcp_call_codex.ps1" `
        -PythonScript "$outputRoot/compile_audio.py" `
        -OutputFile (Join-Path $outputRoot ('compile-editor-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')) `
        -MaxOutputChars 2400 -RequestTimeoutSeconds 600 -QueueWaitSeconds 300
} else {
    & "$projectRoot/Tools/Build/Build-Editor.ps1" *> "$outputRoot/build_editor.log"
    Write-Output 'Background FPSGAMEEditor build completed.'
}
