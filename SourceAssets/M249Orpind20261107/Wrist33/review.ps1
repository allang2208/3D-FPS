param([string]$Label='before')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
 if(!$held){throw 'Review wait expired'}
 $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
 if($busy.Count){throw 'Existing process retained'}
 $out="$PSScriptRoot/native_$Label"
 if(Test-Path -LiteralPath $out){throw 'Output exists'}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" -run=M24HoldReview "-M249ReloadManifest=$PSScriptRoot/manifest_$Label.json" "-Output=$out" -unattended -AllowCommandletRendering -RenderOffscreen -NoSound -NoP4 '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$PSScriptRoot/native_$Label.log" *> "$PSScriptRoot/native_$Label.console"
 $code=$LASTEXITCODE
 Get-Content "$PSScriptRoot/native_$Label.log" -Tail 6
 if($code -ne 0){throw "Native capture exit $code"}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
