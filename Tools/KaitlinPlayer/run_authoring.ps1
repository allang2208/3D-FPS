param([string]$Stage='assemble',[switch]$AllowMainProjectEditor)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$workRoot=Join-Path $projectRoot 'SourceAssets/KaitlinPlayer20261023'
$hostProject=Join-Path $workRoot 'AuthorHost/KaitlinAuthor.uproject'
$scriptFile=Join-Path $projectRoot ('Tools/KaitlinPlayer/'+$Stage+'.py')
$stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$log=Join-Path $workRoot ($Stage+'-'+$stamp+'.log')
$stdout=Join-Path $workRoot ($Stage+'-'+$stamp+'.stdout.txt')
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    Write-Output 'Waiting for the shared asset authoring batch.'
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    while($true) {
        $busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') })
        # This host only writes its own SourceAssets/AuthorHost/Content tree.
        # A running FPSGAME editor does not load these physical packages.
        if($AllowMainProjectEditor) {
            $busy=@($busy | Where-Object {
                -not ($_.Name -eq 'UnrealEditor.exe' -and
                    $_.CommandLine.Replace('\','/').Contains($projectRoot+'/FPSGAME.uproject'))
            })
        }
        # Native extraction reads only this isolated host's saved packages and
        # writes geometry JSON outside Content. Other project commandlets cannot
        # overwrite these inputs; builds and a second process of this host wait.
        if($Stage -eq 'extract_native') {
            $busy=@($busy | Where-Object {
                $_.Name -notin @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -or
                    $_.CommandLine.Replace('\','/').Contains($hostProject.Replace('\','/'))
            })
        }
        if(-not $busy.Count) {break}
        Write-Output 'Waiting for the current engine/build process to finish.'
        try {Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {} catch {if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue) {throw}}
    }
    Write-Output ('Authoring log: '+$log)
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $hostProject '-run=pythonscript' "-script=$scriptFile" '-unattended' '-nop4' '-nosplash' '-nosound' '-AllowCommandletRendering' '-RenderOffscreen' '-ExecCmds=TextureGraph.AllowCommandlets 1,Editor.AsyncSkinnedAssetCompilation 0' '-d3d12' '-sm6' "-abslog=$log" *> $stdout
    $result=$LASTEXITCODE
    Write-Output ('Authoring exit='+$result)
    Get-Content -LiteralPath $stdout -Tail 10
    exit $result
} finally {
    if($held) {$gate.ReleaseMutex()}
    $gate.Dispose()
}
