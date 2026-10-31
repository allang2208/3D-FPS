$ErrorActionPreference='Stop'
$pcgGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$pcgHeld=$false
try {
 $pcgHeld=$pcgGate.WaitOne([TimeSpan]::FromSeconds(900))
 if(-not $pcgHeld){throw 'UE production queue busy; authoring build deferred.'}
 $pcgProcesses=@(Get-CimInstance Win32_Process)
 if($pcgProcesses | Where-Object {$_.Name -in @('UnrealEditor-Cmd.exe','UnrealBuildTool.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}){throw 'Preserving active UE build; authoring build deferred.'}
 # A different project and output DLL: the running FPSGAME editor is untouched.
 & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' CityAuthoringEditor Win64 Development "-Project=$PSScriptRoot/AuthoringHost/CityAuthoring.uproject" -NoHotReloadFromIDE *> "$PSScriptRoot/authoring-build.log"
 $pcgExit=$LASTEXITCODE
 @{exit_code=$pcgExit;game_run=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/authoring-build.json" -Encoding utf8
 if($pcgExit -ne 0){throw "PCG authoring build failed with $pcgExit"}
} finally {if($pcgHeld){$pcgGate.ReleaseMutex()};$pcgGate.Dispose()}
