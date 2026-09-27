param([int]$WaitSeconds=900)
$ErrorActionPreference='Stop'
$projectRoot='D:\FPS3D\FPSGAME'
$logs=Join-Path $projectRoot 'Saved\BowSightContact20260926'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$projectRoot\SourceAssets\BowAudioStillNorth20260926\run_background.ps1" -BuildOnly -WaitSeconds $WaitSeconds -BuildLogName 'build-bow-sight-contact-v11-20260926.log' *> "$logs\build-console.log"
if($LASTEXITCODE -ne 0){throw 'Background build failed; see build-console.log.'}
$deadline=[DateTime]::UtcNow.AddSeconds($WaitSeconds)
while(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME'}){
    if([DateTime]::UtcNow -ge $deadline){throw 'UE still running; no process was closed.'}
    Start-Sleep -Seconds 5
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$projectRoot\SourceAssets\DarkBow20260925\Scripts\run_headless.ps1" -Script "$PSScriptRoot\import_assets.py" -LogName 'bow-sight-contact-v11-import.log' -MutexWaitSeconds $WaitSeconds *> "$logs\import-console.log"
if($LASTEXITCODE -ne 0){throw 'Asset import failed; see import-console.log.'}
& py -3.11 "$PSScriptRoot\install_config.py"
if($LASTEXITCODE -ne 0){throw 'Catalog activation failed.'}
Write-Output 'BOW_SIGHT_CONTACT_V11_SAVED_AND_BUILT'
