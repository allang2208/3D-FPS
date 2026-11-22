param([ValidateSet('floor','install','publish')][string]$Step='install',[string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$contentTarget=@((Get-Item -LiteralPath "$project/Content").Target)[0]
$batch=Join-Path (Split-Path -Parent $contentTarget) 'ArtProduction/HillsVillageShops/CarpenterYard-20261122'
$run=Join-Path $batch (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
New-Item -ItemType Directory -Force -Path $run | Out-Null
if($Step -eq 'publish' -and (Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue)) {
    & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$PSScriptRoot/publish.py" -OutputFile "$run/bridge.json" -MaxOutputChars 2200 -QueueWaitSeconds 300 -RequestTimeoutSeconds 120
    if($LASTEXITCODE -ne 0 -or !(Test-Path "$batch/published.json")) {throw "Publication deferred; see $run/bridge.json"}
    return
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    if ($Step -eq 'publish') {
        if(Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue) {throw 'Editor started, retry with live bridge.'}
        & py -3 "$PSScriptRoot/publish.py"
        if($LASTEXITCODE -ne 0) {throw 'Map publication failed'}
        return
    }
    $uproject="$project/FPSGAME.uproject"
    if ($Step -eq 'install') {
        . (Join-Path $PSScriptRoot 'stage_host.ps1')
        $uproject=New-YardAuthorHost $project $run $contentTarget
    }
    $env:CARPENTER_YARD_RUN=$run
    $log=Join-Path $run "$Step.log"
    $exe=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $argsList=@(('"'+$uproject+'"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="'+$PSScriptRoot+'/'+$Step+'.py"'),'-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite','-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False','-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False','-ExecCmds="Interchange.FeatureFlags.Import.FBX 0"',('-abslog="'+$log+'"'))
    $proc=Start-Process -FilePath $exe -ArgumentList $argsList -WindowStyle Hidden -PassThru
    $null=$proc.Handle
    $proc.WaitForExit()
    $proc.Refresh()
    $receipt=if($Step -eq 'publish') {"$batch/published.json"} else {"$run/$Step.json"}
    if($proc.ExitCode -ne 0 -or !(Test-Path -LiteralPath $receipt)) {throw "Carpenter $Step failed: $log"}
    Write-Output $receipt
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
