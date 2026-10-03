$ErrorActionPreference = 'Stop'
$taskProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskRecordPath = Join-Path $PSScriptRoot 'build.json'
$taskConsolePath = Join-Path $PSScriptRoot ('build-console-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
$taskRecord = Get-Content -LiteralPath $taskRecordPath -Raw | ConvertFrom-Json
$taskDeadline = [DateTime]::UtcNow.AddMinutes(40)
$taskRecord.status = 'WaitingForExistingBuild'
$taskRecord | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskRecordPath -Encoding utf8

try {
    $taskAnnounced = $false
    while ($true) {
        $taskBuilds = @(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool\.dll') -or
            $_.Name -eq 'UnrealBuildTool.exe' -or
            ($_.Name -match '^(cl|link)\.exe$' -and $_.CommandLine -match '/Intermediate/Build/|\\Intermediate\\Build\\') -or
            ($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and
                ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject'))
        })
        if ($taskBuilds.Count -eq 0) { break }
        if (!$taskAnnounced) { Write-Output 'Waiting for existing UE build or project DLL occupation; no competing build submitted.'; $taskAnnounced = $true }
        if ([DateTime]::UtcNow -gt $taskDeadline) { throw 'Existing UE build or project DLL occupation did not release within 40 minutes.' }
        Start-Sleep -Seconds 5
    }
    $taskRecord.status = 'Building'
    $taskRecord.PSObject.Properties.Remove('error')
    $taskRecord | Add-Member -NotePropertyName build_started_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    $taskRecord | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskRecordPath -Encoding utf8
    Write-Output 'Starting ordinary FPSGAMEEditor Win64 Development build.'
    & (Join-Path $taskProjectRoot 'Tools/Build/Build-Editor.ps1') *> $taskConsolePath
    $taskRecord.status = 'EditorBuildCompleted'
    $taskRecord.ordinary_editor_build_completed = $true
    $taskRecord.occupied_editor_pid = $null
    $taskRecord.observed_other_ubt_pid = $null
    $taskRecord | Add-Member -NotePropertyName build_completed_utc -NotePropertyValue ([DateTime]::UtcNow.ToString('o')) -Force
    $taskDll = Get-Item -LiteralPath (Join-Path $taskProjectRoot 'Binaries/Win64/UnrealEditor-FPSGAME.dll')
    $taskRecord | Add-Member -NotePropertyName editor_dll -NotePropertyValue $taskDll.FullName -Force
    $taskRecord | Add-Member -NotePropertyName editor_dll_written_utc -NotePropertyValue $taskDll.LastWriteTimeUtc.ToString('o') -Force
    $taskRecord | Add-Member -NotePropertyName console_log -NotePropertyValue $taskConsolePath -Force
    $taskRecord | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskRecordPath -Encoding utf8
    Get-Content -LiteralPath $taskConsolePath -Tail 8
}
catch {
    $taskRecord.status = 'BuildFailed'
    $taskRecord | Add-Member -NotePropertyName error -NotePropertyValue $_.Exception.Message -Force
    $taskRecord | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskRecordPath -Encoding utf8
    if (Test-Path -LiteralPath $taskConsolePath) { Get-Content -LiteralPath $taskConsolePath -Tail 35 }
    Write-Output $_.Exception.Message
    exit 1
}
