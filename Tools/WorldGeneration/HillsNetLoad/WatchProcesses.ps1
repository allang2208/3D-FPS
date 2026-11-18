param([Parameter(Mandatory=$true)][string]$Run)
$ErrorActionPreference='Stop'
$samples=[Collections.Generic.List[object]]::new()
$deadline=[DateTime]::UtcNow.AddMinutes(35)
while(-not(Test-Path -LiteralPath "$Run/launch-host.json")){
 if((Test-Path -LiteralPath "$Run/failure.json") -or [DateTime]::UtcNow -gt $deadline){return}
 Start-Sleep -Seconds 3
}
do{
 $now=(Get-Date).ToString('o')
 $processes=@(Get-CimInstance Win32_Process | Where-Object {
  $_.Name -in 'UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe','r5apex_dx12.exe' -or
  [long]$_.WorkingSetSize -ge 1GB -or
  ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
 } | ForEach-Object {
  @{pid=$_.ProcessId;name=$_.Name;test_process=($_.CommandLine -like "*$Run/Host/FPSGAME.uproject*");working_set_bytes=[long]$_.WorkingSetSize;
    engine_or_compiler=($_.Name -in 'UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool'))}
 })
 $samples.Add(@{at=$now;processes=$processes})
 Start-Sleep -Seconds 3
}while(-not(Test-Path -LiteralPath "$Run/summary.json") -and -not(Test-Path -LiteralPath "$Run/failure.json") -and [DateTime]::UtcNow -lt $deadline)
@{sampling_seconds=3;samples=$samples}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath "$Run/process-samples.json"
Write-Output "HILLS_PROCESS_SAMPLES_SAVED $Run"
