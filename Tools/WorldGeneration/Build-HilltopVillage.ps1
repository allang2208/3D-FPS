param([string]$Batch='HillsHilltopVillage20261117')
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$out=Join-Path $project ('SourceAssets/'+$Batch)
New-Item -ItemType Directory -Force -Path "$out/Logs" | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    while($true) {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe','FPSGAME.exe','UnrealBuildTool.exe','cl.exe','link.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $busy.Count){break}
        Write-Output 'Waiting for the current asset/build process to finish; no process will be stopped.'
        try {Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop}
        catch [System.TimeoutException] {}
        catch {if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    foreach($target in @('FPSGAMEEditor','FPSGAME')) {
        $log="$out/Logs/$target-build.log"
        $buildCommand='""E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat" '+$target+' Win64 Development "-Project='+$project+'/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -NoUBALocal -NoXGE -NoSNDBS -NoFASTBuild -MaxParallelActions=4 "-Log='+$log+'""'
        $process=Start-Process -FilePath $env:ComSpec -ArgumentList @('/d','/s','/c',$buildCommand) -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput "$out/Logs/$target-stdout.log" -RedirectStandardError "$out/Logs/$target-stderr.log"
        @{target=$target;exit_code=$process.ExitCode;log=$log;finished=(Get-Date).ToString('o');runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$out/$target-build.json" -Encoding utf8
        if($process.ExitCode -ne 0){exit $process.ExitCode}
    }
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
