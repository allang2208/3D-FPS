$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME'
$engine='E:/Program Files (x86)/UE_5.8'
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$receipt=[ordered]@{editorBuilt=$false;gameBuilt=$false;authorityAuditCompleted=$false;socketTested=$false;stamp=$stamp}
try {
    for($attempt=0;$attempt -lt 180 -and -not $held;$attempt++) {
        try{$held=$gate.WaitOne(10000)}catch [Threading.AbandonedMutexException]{$held=$true}
        if(-not $held -and $attempt%6 -eq 0){Write-Output 'Waiting for the existing UE build/asset batch.'}
    }
    if(-not $held){throw 'The shared UE batch remains occupied.'}
    $deadline=[DateTime]::UtcNow.AddMinutes(30);$notice=[DateTime]::UtcNow
    while(@(Get-Process -Name UnrealEditor-Cmd,dotnet,UnrealBuildTool,cl,link -ErrorAction SilentlyContinue).Count) {
        if([DateTime]::UtcNow -gt $deadline){throw 'Existing backend work remains active; no duplicate build started.'}
        if([DateTime]::UtcNow -ge $notice){Write-Output 'Waiting for existing backend work to finish.';$notice=[DateTime]::UtcNow.AddSeconds(60)}
        Start-Sleep -Seconds 5
    }
    if(@(Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue).Count){throw 'Editor is open; source fixes are prepared but ordinary DLL build cannot proceed safely.'}
    Write-Output 'Building the Editor target for M870 quick-melee fixes.'
    & "$project/Tools/Build/Build-Editor.ps1" *> "$PSScriptRoot/editor-build-$stamp.log"
    if($LASTEXITCODE -ne 0){throw 'Editor build failed.'}
    $receipt.editorBuilt=$true
    Write-Output 'Running the requested isolated M870 authority checks.'
    & "$engine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$project/FPSGAME.uproject" -run=ShotgunAttachmentAudit -M870 -nullrhi -unattended -nop4 -nosplash -nosound "-abslog=$PSScriptRoot/authority-engine-$stamp.log" *> "$PSScriptRoot/authority-console-$stamp.log"
    $authorityExit=$LASTEXITCODE
    $report="$project/Saved/M870CompletionAudit20261017/authority-result.json"
    if(Test-Path -LiteralPath $report){Copy-Item -LiteralPath $report -Destination "$PSScriptRoot/authority-result-$stamp.json"}
    if($authorityExit -ne 0){throw "M870 authority audit failed ($authorityExit); see the saved report."}
    $receipt.authorityAuditCompleted=$true
    Write-Output 'Building the Game target for the same runtime fixes.'
    & "$engine/Engine/Build/BatchFiles/Build.bat" FPSGAME Win64 Development "-Project=$project/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles -MaxParallelActions=4 "-Log=$PSScriptRoot/game-build-engine-$stamp.log" *> "$PSScriptRoot/game-build-$stamp.log"
    if($LASTEXITCODE -ne 0){throw 'Game target build failed.'}
    $receipt.gameBuilt=$true
    Write-Output 'M870 quick-melee fixes built; isolated authority audit completed. No socket or visual test.'
} catch {
    $receipt.error=$_.Exception.Message
    throw
} finally {
    $receipt | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/build-receipt-$stamp.json" -Encoding utf8
    if($held){$gate.ReleaseMutex()};$gate.Dispose()
}
