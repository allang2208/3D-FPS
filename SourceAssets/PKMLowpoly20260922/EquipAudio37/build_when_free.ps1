# Wait for the user's open editor to close, then run one incremental Editor build.
# It never stops or touches another process; it only waits for the build guard to clear.
param([int]$TimeoutMinutes=45)
$projectRoot='D:\FPS3D\FPSGAME'
$log=Join-Path $PSScriptRoot 'build_editor.log'
$receipt=Join-Path $PSScriptRoot 'build_receipt.json'
$deadline=(Get-Date).AddMinutes($TimeoutMinutes)
$busy=@()
while((Get-Date) -lt $deadline){
    $busy=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape('FPSGAME.uproject') })
    if($busy.Count -eq 0){ break }
    Start-Sleep -Seconds 20
}
if($busy.Count -ne 0){
    @{status='still-blocked';waited_minutes=$TimeoutMinutes;busy_pid=$busy[0].ProcessId} | ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_status.json') -Encoding UTF8
    Write-Output 'still-blocked'
    exit 3
}
& (Join-Path $projectRoot 'Tools\Build\Build-Editor.ps1') *> $log
$code=$LASTEXITCODE
@{target='FPSGAMEEditor Win64 Development';exit_code=$code;log=$log;runtime_tested=$false;
  trigger='equip-audio change, built after the editor closed'} | ConvertTo-Json |
    Set-Content -LiteralPath $receipt -Encoding UTF8
Write-Output "exit=$code"
exit $code
