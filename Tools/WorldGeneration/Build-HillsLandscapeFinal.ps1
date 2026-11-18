param([string]$Batch='HillsLandscapeRepair20261117Final')
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$out=Join-Path $project ('SourceAssets/'+$Batch)
New-Item -ItemType Directory -Force -Path "$out/Logs" | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    while($true) {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','FPSGAME.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $busy.Count){break}
        try {Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop}
        catch [System.TimeoutException] {}
        catch {if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'An editor is active; retain its loaded module and staged review build.'}
    $receipt=@{targets=@();finished=$null}
    foreach($target in 'FPSGAMEEditor','FPSGAME') {
        $command='""E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat" '+$target+' Win64 Development "-Project='+$project+'/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -NoUBALocal -NoXGE -NoSNDBS -NoFASTBuild -MaxParallelActions=4 "-Log='+$out+'/Logs/'+$target+'.log""'
        $process=Start-Process -FilePath $env:ComSpec -ArgumentList @('/d','/s','/c',$command) -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out/Logs/$target-stdout.log" -RedirectStandardError "$out/Logs/$target-stderr.log"
        $buildHandle=$process.Handle
        while(-not $process.HasExited) {
            $parents=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" | Where-Object {$_.CommandLine -like "*$out*"} | ForEach-Object {$_.ProcessId})
            if($parents.Count) {
                Get-CimInstance Win32_Process -Filter "Name='cl.exe'" | Where-Object {$_.ParentProcessId -in $parents} | ForEach-Object {
                    $compiler=Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
                    if($compiler){try {$compiler.PriorityClass='Normal'} catch {}}
                }
            }
            Start-Sleep -Seconds 2;$process.Refresh()
        }
        $process.WaitForExit()
        $receipt.targets+=@{name=$target;exit_code=$process.ExitCode}
        $receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$out/build.json" -Encoding utf8
        if($process.ExitCode -ne 0){throw "$target build failed: $($process.ExitCode)"}
    }
    $receipt.finished=(Get-Date).ToString('o')
    New-Item -ItemType Directory -Force -Path "$out/Module" | Out-Null
    foreach($file in 'UnrealEditor-FPSGAME.dll','UnrealEditor.modules') {
        Copy-Item -LiteralPath "$project/Binaries/Win64/$file" -Destination "$out/Module/$file"
    }
    $receipt.artifacts=@('UnrealEditor-FPSGAME.dll','FPSGAME.exe') | ForEach-Object {
        $path=Join-Path $project ('Binaries/Win64/'+$_)
        @{path=$path;sha256=(Get-FileHash -LiteralPath $path).Hash}
    }
    $receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath "$out/build.json" -Encoding utf8
    Get-Content -LiteralPath "$out/build.json" -Raw
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
