param([string]$ScriptFile='import_refinement_v3.py',[string]$OutputFolder='RefinementV3',[string]$UnloadedStaffMapContext)
$ErrorActionPreference='Stop'
$taskRoot=Split-Path $PSScriptRoot -Parent
$taskProject=Split-Path (Split-Path $taskRoot -Parent) -Parent
$taskUE='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$taskMutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    try { $taskHeld=$taskMutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
    if (-not $taskHeld) { Write-Output 'Waiting for the current UE asset batch.' }
    while (-not $taskHeld) {
        try { $taskHeld=$taskMutex.WaitOne(5000) } catch [Threading.AbandonedMutexException] { $taskHeld=$true }
    }
    $taskEditors=Get-CimInstance Win32_Process -Filter "Name = 'UnrealEditor.exe'" | Where-Object {$_.CommandLine -like '*FPSGAME*' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)|(?:^|\s)-run='}
    if ($taskEditors) {
        $taskContextAllowed=$false
        if ($UnloadedStaffMapContext -and $ScriptFile -in @('import_intact_tiles_v4.py','import_scene_polish_v4.py','import_room_details_v5.py','import_wall_inset_v6.py','import_coffee_polish_v7.py')) {
            $taskContextFile=Get-Item -LiteralPath $UnloadedStaffMapContext
            $taskContext=Get-Content -LiteralPath $UnloadedStaffMapContext -Raw -Encoding UTF8 | ConvertFrom-Json
            $taskMapValues=@($taskContext.loaded_staff_maps.PSObject.Properties | ForEach-Object {$_.Value})
            $taskContextAllowed=([DateTime]::UtcNow-$taskContextFile.LastWriteTimeUtc).TotalSeconds -lt 30 -and
                @($taskEditors.ProcessId) -contains $taskContext.process_id -and
                $taskMapValues.Count -eq 4 -and @($taskMapValues | Where-Object {$_}).Count -eq 0 -and
                @($taskContext.dirty_maps).Count -eq 0 -and @($taskContext.dirty_staff_assets).Count -eq 0
        }
        if (-not $taskContextAllowed) { throw 'An interactive FPSGAME editor is open; preserve its loaded sample assets and use the existing MCP bridge.' }
    }
    $taskScript=Join-Path $PSScriptRoot $ScriptFile
    $taskOutput=Join-Path $taskRoot $OutputFolder
    $taskLog=Join-Path $taskOutput 'ue-import.log'
    $taskStdout=Join-Path $taskOutput 'ue-import-stdout.log'
    & $taskUE (Join-Path $taskProject 'FPSGAME.uproject') '-run=pythonscript' "-script=$taskScript" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-d3d12' "-abslog=$taskLog" *> $taskStdout
    $taskCode=$LASTEXITCODE
    Write-Output "STAFF_REFINEMENT_IMPORT_EXIT=$taskCode"
    if ($taskCode -ne 0) { throw "Staff refinement import failed. See $taskLog" }
} finally {
    if ($taskHeld) {$taskMutex.ReleaseMutex()}
    $taskMutex.Dispose()
}
