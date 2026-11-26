$ErrorActionPreference='Stop'
$nunProject='D:/FPS3D/FPSGAME'
$nunOut="$nunProject/SourceAssets/ChapelNun20261115/IdleHandsFrontR1"
# Waiting is outside the shared asset mutex so an active user/editor keeps it.
while($true) {
 $nunBusy=@(Get-CimInstance Win32_Process | Where-Object {
  $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or
  ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
 })
 if(-not $nunBusy.Count){break}
 try {Wait-Process -Id $nunBusy[0].ProcessId -Timeout 45 -ErrorAction Stop}
 catch [System.TimeoutException] {}
 catch {if(Get-Process -Id $nunBusy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
}
$nunSaved="$nunOut/saved_asset.json"
if(-not (Test-Path -LiteralPath $nunSaved)) {
 & "$nunProject/Tools/ChapelNun/run_asset.ps1" -Script "$nunProject/Tools/ChapelNun/save_idle_hands_front.py" -Label 'idlefront-save-background'
 if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
}
if(-not (Test-Path -LiteralPath $nunSaved)){throw 'Animation save receipt missing; runtime build not started.'}
& "$nunProject/Tools/ChapelNun/run_idle_build.ps1"
if($LASTEXITCODE -ne 0){exit $LASTEXITCODE}
$nunAsset=Get-Content -LiteralPath $nunSaved -Raw | ConvertFrom-Json
@{
 animation=$nunAsset.asset
 saved=$true
 editor_build='success'
 game_build='success'
 source_blend="$nunOut/Nun_HandsFront_Idle_R1.blend"
 source_motion="$nunOut/authored.json"
 source_reference="$nunOut/standing_reference.png"
 runtime_source='Source/FPSGAME/NPC/ChapelNun.cpp'
 duration_seconds=12
 breath_cycles=3
 runtime_tested=$false
 captured_or_rendered=$false
 completed_at=(Get-Date).ToString('o')
}|ConvertTo-Json|Set-Content -LiteralPath "$nunOut/delivery.json" -Encoding utf8
Write-Output 'NUN_IDLE_INSTALLED'
