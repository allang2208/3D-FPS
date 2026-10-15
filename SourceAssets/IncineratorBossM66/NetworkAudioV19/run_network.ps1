param([int]$Port=17966)
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME';$taskRoot=Join-Path $taskProject 'SourceAssets/IncineratorBossM66/NetworkAudioV19'
$taskEngine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
if(@(Get-CimInstance Win32_Process | Where-Object {($_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME\.uproject')) -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')}).Count){throw 'Project engine/build busy; network fixture not started.'}
$taskRun=Join-Path $taskRoot ('Records/network-'+(Get-Date -Format 'yyyyMMdd-HHmmss'));New-Item -ItemType Directory -Path $taskRun -Force|Out-Null
$taskProcesses=@{}
function Start-M66Peer([string]$Role,[string]$Url) {
    $taskPeerDir=Join-Path $taskRun $Role;New-Item -ItemType Directory -Path $taskPeerDir -Force|Out-Null
    $taskArgs=@(('"'+$taskProject+'/FPSGAME.uproject"'),('"'+$Url+'"'),'-game','-NullRHI','-nosound','-unattended','-nop4','-nosplash','-NoLiveCoding','-NoSteam','-M66NetAudit',
        ('-M66AuditLabel='+$Role),('-port='+$Port),('-ColdSteelProfile=M66Audit_'+$Role+'_'+(Get-Date -Format 'HHmmss')),
        ('"-M66AuditOutput='+$taskPeerDir+'/result.json"'),('"-UserDir='+$taskPeerDir+'/user"'),('"-abslog='+$taskPeerDir+'/engine.log"'),
        '"-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False"')
    $taskProcesses[$Role]=Start-Process -FilePath $taskEngine -ArgumentList $taskArgs -WorkingDirectory $taskProject -WindowStyle Hidden -PassThru
}
try {
    Start-M66Peer 'host' '/Engine/Maps/Entry?listen?game=/Script/FPSGAME.M66NetAuditGameMode'
    $taskDeadline=(Get-Date).AddMinutes(6)
    while((Get-Date)-lt $taskDeadline) {
        $taskHostLog=Join-Path $taskRun 'host/engine.log'
        if(Test-Path -LiteralPath $taskHostLog) {
            $taskText=Get-Content -LiteralPath $taskHostLog -Raw
            if(-not $taskProcesses.ContainsKey('early') -and $taskText.Contains('M66_NET_HOST_READY')){Start-M66Peer 'early' ('127.0.0.1:'+$Port)}
            if(-not $taskProcesses.ContainsKey('late') -and $taskText.Contains('M66_NET_LATE_READY')){Start-M66Peer 'late' ('127.0.0.1:'+$Port)}
        }
        if(Test-Path -LiteralPath (Join-Path $taskRun 'host/result.json')){break}
        if($taskProcesses['host'].HasExited){break}
        Start-Sleep -Seconds 2
    }
    $taskResults=@{}
    foreach($taskRole in @('host','early','late')) {
        $taskResultFile=Join-Path $taskRun ($taskRole+'/result.json')
        if(Test-Path -LiteralPath $taskResultFile){$taskResults[$taskRole]=Get-Content -Raw -LiteralPath $taskResultFile|ConvertFrom-Json}
    }
    $taskSuccess=$taskResults.Count -eq 3 -and $taskResults['host'].result -and $taskResults['early'].result -and $taskResults['late'].result
    [ordered]@{success=[bool]$taskSuccess;run=$taskRun;port=$Port;results=$taskResults}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $taskRun 'summary.json') -Encoding utf8
    if(-not $taskSuccess){throw ('M66 network fixture did not pass; '+$taskRun)}
    Write-Output ('M66 host/early/late passed; '+$taskRun)
} finally {
    foreach($taskProcess in $taskProcesses.Values) {
        if(-not $taskProcess.HasExited){Stop-Process -Id $taskProcess.Id -ErrorAction SilentlyContinue}
    }
}
