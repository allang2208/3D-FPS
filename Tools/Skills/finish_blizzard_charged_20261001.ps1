param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$taskProjectFile=Join-Path $taskProject 'FPSGAME.uproject'
$taskOutput=Join-Path $taskProject 'Saved/BlizzardCharged20261001'
$taskAssetRun=Get-Date -Format 'yyyyMMdd-HHmmss'
[IO.Directory]::CreateDirectory($taskOutput)|Out-Null
$taskState=[ordered]@{assetsSaved=$false;gameBuild='pending';editorBuild='pending';gameplayTested=$false;rendered=$false}
function Save-State {
 [IO.File]::WriteAllText((Join-Path $taskOutput 'delivery.json'),($taskState|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
}
function Project-Editors {
 @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {($_.CommandLine -replace '\\','/') -match [regex]::Escape(($taskProjectFile -replace '\\','/'))})
}
function Wait-BuildWindow {
 do {
  $taskBusy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealBuildTool.exe' -or $_.Name -in @('cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
  $taskCmd=@(Project-Editors | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' })
  if($taskBusy.Count -or $taskCmd.Count){Write-Host ('Waiting for existing build/asset processes: '+(($taskBusy+$taskCmd|Select-Object -ExpandProperty ProcessId)-join ','));Start-Sleep -Seconds 15}
 }while($taskBusy.Count -or $taskCmd.Count)
}
Save-State
Wait-BuildWindow
$taskAuthor=Join-Path $PSScriptRoot 'build_blizzard_charged_v3.py'
if(@(Project-Editors | Where-Object { $_.Name -eq 'UnrealEditor.exe' }).Count){
 & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskAuthor -OutputFile (Join-Path $taskOutput ("asset-bridge-$taskAssetRun.txt")) -MaxOutputChars 3000
 if($LASTEXITCODE -ne 0){throw 'Asset bridge failed; retain saved packages.'}
}else{
 & (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') $taskProjectFile -run=pythonscript "-script=$taskAuthor" -unattended -nop4 -nosplash -NullRHI -nosound "-abslog=$(Join-Path $taskOutput ("asset-commandlet-$taskAssetRun.log"))" *> (Join-Path $taskOutput ("asset-commandlet-output-$taskAssetRun.log"))
 if($LASTEXITCODE -ne 0){throw 'Asset commandlet failed; retain saved packages.'}
}
$taskReceipt=Get-Content (Join-Path $taskOutput 'asset-authoring.json') -Raw|ConvertFrom-Json
if($taskReceipt.saved_assets -notcontains '/Game/Skills/Blizzard/ChargedV3/M_BlizzardIceHeart.M_BlizzardIceHeart'){throw 'Missing saved instanced ice material receipt.'}
$taskState.assetsSaved=$true;Save-State
Wait-BuildWindow
$taskBuild=Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat'
& $taskBuild FPSGAME Win64 Development "-Project=$taskProjectFile" -NoHotReload -NoHotReloadFromIDE "-Log=$(Join-Path $taskOutput 'build-game.log')"
if($LASTEXITCODE -ne 0){$taskState.gameBuild='failed';Save-State;throw 'Game build failed.'}
$taskState.gameBuild='succeeded';Save-State
Wait-BuildWindow
$taskLocked=$false
try{$taskStream=[IO.File]::Open((Join-Path $taskProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll'),'Open','ReadWrite','None');$taskStream.Dispose()}catch{$taskLocked=$true}
if((Project-Editors).Count -or $taskLocked){$taskState.editorBuild='pending-editor-close';Save-State;Write-Host 'Assets and Game saved; ordinary Editor needs the editor closed.';exit 10}
& $taskBuild FPSGAMEEditor Win64 Development "-Project=$taskProjectFile" -NoHotReload -NoHotReloadFromIDE "-Log=$(Join-Path $taskOutput 'build-editor.log')"
if($LASTEXITCODE -ne 0){$taskState.editorBuild='failed';Save-State;throw 'Editor build failed.'}
$taskState.editorBuild='succeeded';Save-State
Write-Host 'Blizzard ChargedV3 assets and ordinary Game/Editor builds saved. No gameplay tests.'
