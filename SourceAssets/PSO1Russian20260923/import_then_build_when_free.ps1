# Wait for the user's editor to close, then import the re-authored PKM PSO and rebuild.
# It never stops or touches another process; it only waits for the batch gate to clear.
param([int]$TimeoutMinutes=120)
$case='D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923'
$deadline=(Get-Date).AddMinutes($TimeoutMinutes)
$busy=@()
while((Get-Date) -lt $deadline){
    $busy=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME' })
    if($busy.Count -eq 0){ break }
    Start-Sleep -Seconds 20
}
if($busy.Count -ne 0){
    @{status='still-blocked';waited_minutes=$TimeoutMinutes;busy_pid=$busy[0].ProcessId} | ConvertTo-Json |
        Set-Content -LiteralPath "$case\import_topmount_status.json" -Encoding UTF8
    Write-Output 'still-blocked'
    exit 3
}
& "$case\background.ps1" -Script 'import_assets.py' *> "$case\import_topmount.log"
$import=$LASTEXITCODE
# The import's own UnrealEditor-Cmd can outlive the script call by seconds; give the
# build guard a clear window instead of racing it.
for($i=0;$i -lt 15;$i++){
    $left=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME' })
    if($left.Count -eq 0){ break }
    Start-Sleep -Seconds 20
}
& 'D:\FPS3D\FPSGAME\Tools\Build\Build-Editor.ps1' *> "$case\build_topmount.log"
$build=$LASTEXITCODE
@{import_exit=$import;build_exit=$build;runtime_tested=$false;
  trigger='PKM PSO extracted-body top mount, run after the editor closed'} | ConvertTo-Json |
    Set-Content -LiteralPath "$case\import_topmount_receipt.json" -Encoding UTF8
Write-Output "import=$import build=$build"
exit $build
