param([string]$Script='read_authoring_inputs.py',[string]$RunName='read-inputs',[switch]$CompileShaders,[int]$QueueWaitSeconds=60)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$engineCommand='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$logRoot=Join-Path $PSScriptRoot 'Receipts'
[IO.Directory]::CreateDirectory($logRoot) | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try { $held=$gate.WaitOne($QueueWaitSeconds*1000) } catch [Threading.AbandonedMutexException] { $held=$true }
    if(-not $held){ throw 'Production batch is busy; no engine process started.' }
    $active=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -like '*FPSGAME.uproject*' }
    if($active){ throw 'FPSGAME is already loaded; preserve its assets and use its MCP batch.' }
    $args=@(('"'+$projectRoot+'/FPSGAME.uproject"'),'-run=pythonscript',('-script="'+(Join-Path $PSScriptRoot $Script)+'"'),'-Unattended','-NoSplash','-NoSound','-NoLiveCoding',('-abslog="'+(Join-Path $logRoot ($RunName+'-engine.log'))+'"'),'-stdout','-FullStdOutLogOutput')
    # Use the real shader platform for material production, without PIE or a
    # viewport capture. NullRHI cannot report SM6 sampler/translation failures.
    if($CompileShaders){$args+=@('-AllowCommandletRendering','-RenderOffscreen')}else{$args+='-NullRHI'}
    $p=Start-Process -FilePath $engineCommand -ArgumentList $args -WorkingDirectory $projectRoot -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $logRoot ($RunName+'-stdout.log')) -RedirectStandardError (Join-Path $logRoot ($RunName+'-stderr.log'))
    Write-Output ('Background commandlet exit: '+$p.ExitCode)
    exit $p.ExitCode
} finally { if($held){$gate.ReleaseMutex()};$gate.Dispose() }
