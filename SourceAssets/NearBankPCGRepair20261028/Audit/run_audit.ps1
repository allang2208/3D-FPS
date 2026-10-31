param([string]$Run='capture-01',[string]$Script='export_scene.py',[switch]$RefreshSnapshot)
$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(900))} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'UE window busy; no audit process started'}
 if(Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}){throw 'Existing background UE job preserved'}
 $root=[IO.Path]::GetFullPath("$PSScriptRoot/../PublicationHost")
 if($RefreshSnapshot){
  $receipts=@()
  foreach($folder in @('GameMaps','NativeNearBank20261028')){
   $dest=Get-Item -LiteralPath "$root/Content/$folder"
   if($dest.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Snapshot target must be a physical owned directory'}
   $source="D:/FPS3D/FPSGAME/Content/$folder"
   foreach($file in Get-ChildItem -LiteralPath $source -Recurse -File){
    $rel=$file.FullName.Substring($source.Length+1);$out=Join-Path $dest.FullName $rel
    New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($out)) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $out -Force
    $receipts+=@{path="$folder/$rel";bytes=$file.Length;sha256=(Get-FileHash -LiteralPath $out -Algorithm SHA256).Hash}
   }
  }
  @{captured_at=(Get-Date).ToString('o');files=$receipts;source='formal saved project';no_formal_asset_writes=$true} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$PSScriptRoot/snapshot.json" -Encoding utf8
 }
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$root/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended -nosplash -nosound -nullrhi '-DisablePlugins=USDImporter,InterchangeOpenUSD,InterchangeOpenUSDChaosClothAsset,ChaosClothAssetUsdDataflowNodes,USDMultiUser,USDImporterMDL,USDPregen,ChaosCachingUSD,USDCore,CLOLiveSync,FabLauncher,ChaosFlesh' "-abslog=$PSScriptRoot/$Run.log" *> "$PSScriptRoot/$Run-console.log"
 $exit=$LASTEXITCODE
 @{exit_code=$exit;script=$Script;game_run=$false;graphical_editor_started=$false;formal_assets_written=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/$Run.json" -Encoding utf8
 if($exit -ne 0){throw "Audit failed: $Run.log"}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
