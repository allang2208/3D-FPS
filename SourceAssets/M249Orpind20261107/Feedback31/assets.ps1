param([string]$Script='collect.py')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
 if(!$held){throw 'Shared asset window wait expired'}
 $deadline=[DateTime]::UtcNow.AddMinutes(20)
 do {
  $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
  if($busy.Count){if([DateTime]::UtcNow -gt $deadline){throw 'Existing process retained'};Start-Sleep -Seconds 5}
 }while($busy.Count)
 $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'")
 if($editors.Count){throw 'Editor opened; use existing editor bridge for assets'}
 $env:UE_SKIP_UBT_SDK_SETUP='1'
 $log="$PSScriptRoot/$Script.log"
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended -NullRHI -NoSound -NoP4 "-abslog=$log" *> "$log.console"
 $code=$LASTEXITCODE
 Get-Content -LiteralPath $log -Tail 6
 if($code -ne 0){throw "Asset commandlet exit $code"}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
