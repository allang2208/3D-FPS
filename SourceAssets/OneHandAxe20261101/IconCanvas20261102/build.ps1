param([string[]]$Targets = @('FPSGAMEEditor', 'FPSGAME'))
$ErrorActionPreference = 'Stop'
$batch = $PSScriptRoot
$project = 'D:/FPS3D/FPSGAME/FPSGAME.uproject'
$active = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(UnrealEditor|UnrealEditor-Cmd|FPSGAME|FPSGAME-Win64-Shipping|cl|link)\.exe$' -or
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
})
if ($active.Count -gt 0) { throw 'An editor, game or native build is active. Preserve it and wait before submitting this build.' }
$results = @()
foreach ($target in $Targets) {
    # Use the standard Editor arguments, so this batch can reuse the shared
    # build instead of changing its Live Coding compile configuration again.
    $arguments = @($target, 'Win64', 'Development', "-Project=$project", '-WaitMutex', '-NoHotReloadFromIDE')
    if ($target -eq 'FPSGAMEEditor') { $arguments += @('-NoHotReload', '-NoUBTMakefiles') }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' @arguments *> "$batch/build-$target.log"
    $code = $LASTEXITCODE
    $results += [ordered]@{target=$target;exit_code=$code;log="build-$target.log"}
    $results | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath "$batch/build_receipt.json" -Encoding utf8
    Write-Output "$target exit=$code"
    if ($code -ne 0) { exit $code }
}
