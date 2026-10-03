param([int]$WaitSeconds=1800)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$deadline=[DateTime]::UtcNow.AddSeconds($WaitSeconds)
$waiting=$false
while($true) {
    $processes=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe'")
    $busy=@($processes | Where-Object {
        ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and
            ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
        $_.Name -eq 'cl.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
    })
    if($busy.Count -eq 0){break}
    if(-not $waiting){Write-Output 'Waiting for occupied project binaries/build window; no processes will be stopped.';$waiting=$true}
    if([DateTime]::UtcNow -ge $deadline){throw 'Background build is pending: project binaries are still occupied.'}
    Start-Sleep -Seconds 10
}
Write-Output 'Project binaries are available. Starting the regular FPSGAMEEditor build.'
& (Join-Path $projectRoot 'Tools/Build/Build-Editor.ps1')
if($LASTEXITCODE -ne 0){throw "Build exit code $LASTEXITCODE"}
$receipt=Join-Path $PSScriptRoot 'build_receipt.json'
@{native_class_built=$true;target='FPSGAMEEditor Win64 Development';finished_utc=[DateTime]::UtcNow.ToString('o');tested=$false}|ConvertTo-Json|Set-Content -LiteralPath $receipt -Encoding UTF8