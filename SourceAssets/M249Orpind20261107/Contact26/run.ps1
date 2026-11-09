param([string]$Manifest='manifest.json',[string]$Label='before')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
if($Label -eq 'final'){while(!(Test-Path -LiteralPath "$PSScriptRoot/publish-ready.json")){Start-Sleep -Seconds 3}}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(25))}catch [Threading.AbandonedMutexException]{$held=$true}
 if(!$held){throw 'Shared review window wait expired'}
 do {
  $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
  if($busy.Count){Start-Sleep -Seconds 5}
 }while($busy.Count)
 $out="$PSScriptRoot/$Label";if(Test-Path -LiteralPath $out){throw 'Review output already exists'}
 $env:UE_SKIP_UBT_SDK_SETUP='1'
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" -run=M24HoldReview "-M249ReloadManifest=$PSScriptRoot/$Manifest" "-Output=$out" -unattended -AllowCommandletRendering -RenderOffscreen -NoSound -NoP4 "-abslog=$PSScriptRoot/$Label.log" *> "$PSScriptRoot/$Label.console.txt"
 $code=$LASTEXITCODE
 @{exit_code=$code;finished=(Get-Date -Format o);editor_gui_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/$Label.process.json"
 Get-Content -LiteralPath "$PSScriptRoot/$Label.log" -Tail 8
 if($code -ne 0){throw "Reload review exit $code"}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
