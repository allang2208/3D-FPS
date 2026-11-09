param([string]$Label='before')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
 if(!$held){throw 'Shared review window wait expired'}
 $deadline=[DateTime]::UtcNow.AddMinutes(20)
 do {
  $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
  if($busy.Count){if([DateTime]::UtcNow -gt $deadline){throw 'Existing process retained'};Start-Sleep -Seconds 5}
 }while($busy.Count)
 if(@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'").Count){throw 'Existing editor retained'}
 $out="$PSScriptRoot/$Label";if(Test-Path -LiteralPath $out){throw 'Review output already exists'}
 $env:UE_SKIP_UBT_SDK_SETUP='1'
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" -run=M24HoldReview "-M249ReloadManifest=$PSScriptRoot/manifest.json" "-Output=$out" -unattended -AllowCommandletRendering -RenderOffscreen -NoSound -NoP4 "-abslog=$PSScriptRoot/$Label.log" *> "$PSScriptRoot/$Label.console.txt"
 $code=$LASTEXITCODE
 Get-Content -LiteralPath "$PSScriptRoot/$Label.log" -Tail 6
 if($code -ne 0){throw "Reload review exit $code"}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
