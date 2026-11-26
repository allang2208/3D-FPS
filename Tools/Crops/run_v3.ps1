param([ValidateSet('import','readback')][string]$Phase='import',[switch]$RefreshLODs)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new()
$projectRoot='D:\FPS3D\FPSGAME'
$taskRoot=Join-Path $projectRoot 'SourceAssets\CropsV3_20261022'
$hostRoot=Join-Path $projectRoot 'Saved\CropsV3ImportHost'
$engineCmd='E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$projectFile=Join-Path $hostRoot 'CropsV3Import.uproject'
$scriptFile=Join-Path $PSScriptRoot 'ue_import_v3.py'
New-Item -ItemType Directory -Path (Join-Path $hostRoot 'Config') -Force | Out-Null
if(-not(Test-Path -LiteralPath $projectFile)){
    $definition=@{FileVersion=3;EngineAssociation='5.8';Plugins=@(
        @{Name='PythonScriptPlugin';Enabled=$true},
        @{Name='EditorScriptingUtilities';Enabled=$true},
        @{Name='GeometryScripting';Enabled=$true}
    )}|ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText($projectFile,$definition,[Text.UTF8Encoding]::new($false))
    [IO.File]::WriteAllText((Join-Path $hostRoot 'Config\DefaultEngine.ini'),"[/Script/Engine.RendererSettings]`nr.Substrate=True`n",[Text.UTF8Encoding]::new($false))
}
# This host never loads FPSGAME DLLs or writes any package outside its own Content.
# Share the asset-operation mutex with the project bridge for the complete commandlet.
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try{
    try{$held=$mutex.WaitOne([TimeSpan]::FromSeconds(60))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){Write-Output 'Asset mutex busy; commandlet was not started.';exit 75}
    $own=Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -like '*CropsV3Import.uproject*' }
    if($own){throw 'This crop commandlet is already running; refusing duplicate launch.'}
    $log=Join-Path $taskRoot ('Receipts\ue-'+$Phase+'.log')
    $arguments=@(('"'+$projectFile+'"'),'-run=pythonscript',('-script="'+$scriptFile+'"'),
        '-CropsV3AssetBatch','-unattended','-nop4','-nosplash','-nullrhi','-nosound','-NoShaderCompile','-multiprocess',
        ('-UserDir="'+(Join-Path $hostRoot 'User')+'"'),('-abslog="'+$log+'"'))
    if($Phase -eq 'readback'){$arguments+='-CropsV3Readback'}
    if($RefreshLODs){$arguments+='-CropsV3RefreshLODs'}
    $job=Start-Process -FilePath $engineCmd -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $processReceipt=Join-Path $taskRoot ('Receipts\ue-'+$Phase+'-process.json')
    [IO.File]::WriteAllText($processReceipt,(@{pid=$job.Id;startUtc=[DateTime]::UtcNow.ToString('o');phase=$Phase;project=$projectFile}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    Write-Output ('Started hidden Crops V3 '+$Phase+' commandlet PID '+$job.Id)
    $job.WaitForExit();$job.Refresh()
    [IO.File]::WriteAllText((Join-Path $taskRoot ('Receipts\ue-'+$Phase+'-exit.json')),(@{exitCode=$job.ExitCode;endUtc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
    Write-Output ($Phase+' exit: '+$job.ExitCode)
    exit $job.ExitCode
}finally{if($held){$mutex.ReleaseMutex()};$mutex.Dispose()}
