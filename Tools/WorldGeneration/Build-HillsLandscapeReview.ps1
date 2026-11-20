param([string]$Batch='HillsLandscapeRepair20261117',[switch]$EditorOnly)
$ErrorActionPreference='Stop'
$project=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$out=Join-Path $project ('SourceAssets/'+$Batch)
New-Item -ItemType Directory -Force -Path "$out/Logs","$out/Module" | Out-Null
function Wait-OwnBuild([Diagnostics.Process]$BuildProcess) {
    while(-not $BuildProcess.HasExited) {
        # Only this batch's UBT children receive ordinary scheduling priority.
        $parents=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe'" |
            Where-Object {$_.CommandLine -like "*$out*"} | ForEach-Object {$_.ProcessId})
        if($parents.Count) {
            Get-CimInstance Win32_Process -Filter "Name='cl.exe'" |
                Where-Object {$_.ParentProcessId -in $parents} | ForEach-Object {
                    $compiler=Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue
                    if($compiler){try {$compiler.PriorityClass='Normal'} catch {}}
                }
        }
        Start-Sleep -Seconds 2
        $BuildProcess.Refresh()
    }
    $BuildProcess.WaitForExit()
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    while($true) {
        $busy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('UnrealBuildTool.exe','cl.exe','link.exe','FPSGAME.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if(-not $busy.Count){break}
        Write-Output 'Waiting for an existing build; no process will be stopped.'
        try {Wait-Process -Id $busy[0].ProcessId -Timeout 45 -ErrorAction Stop} catch [System.TimeoutException] {}
        catch {if(Get-Process -Id $busy[0].ProcessId -ErrorAction SilentlyContinue){throw}}
    }
    # UBT emits its normal current response files, but executes only compilation.
    # The active editor's DLL, PDB and module manifest are never link outputs here.
    $buildCommand='""E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat" FPSGAMEEditor Win64 Development "-Project='+$project+'/FPSGAME.uproject" -gather -ActionTypeFilter=Compile -NoHotReload -NoHotReloadFromIDE -NoUBA -NoUBALocal -NoXGE -NoSNDBS -NoFASTBuild -MaxParallelActions=4 "-Log='+$out+'/Logs/Editor-compile.log""'
    $compile=Start-Process -FilePath $env:ComSpec -ArgumentList @('/d','/s','/c',$buildCommand) -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out/Logs/Editor-stdout.log" -RedirectStandardError "$out/Logs/Editor-stderr.log"
    Wait-OwnBuild $compile
    if($compile.ExitCode -ne 0){throw "Editor compile failed: $($compile.ExitCode)"}
    $rspSource="$project/Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME/UnrealEditor-FPSGAME.dll.rsp"
    $rspText=[IO.File]::ReadAllText($rspSource)
    $moduleDir=([IO.Path]::GetFullPath("$out/Module")).Replace('\','/')
    $rspText=[regex]::Replace($rspText,'(?m)^/OUT:.*$',('/OUT:"'+$moduleDir+'/UnrealEditor-FPSGAME.dll"'))
    $rspText=[regex]::Replace($rspText,'(?m)^/PDB:.*$',('/PDB:"'+$moduleDir+'/UnrealEditor-FPSGAME.pdb"'))
    $rspText+="`r`n/IMPLIB:`"$moduleDir/UnrealEditor-FPSGAME.lib`"`r`n"
    $rsp="$out/Module/Review-link.rsp"
    [IO.File]::WriteAllText($rsp,$rspText,[Text.UTF8Encoding]::new($false))
    $link=Start-Process -FilePath 'C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/link.exe' -ArgumentList ('@"'+$rsp+'"') -WorkingDirectory 'E:/Program Files (x86)/UE_5.8/Engine/Source' -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out/Logs/Editor-link.log" -RedirectStandardError "$out/Logs/Editor-link-stderr.log"
    $link.WaitForExit()
    if($link.ExitCode -ne 0){throw "Isolated editor link failed: $($link.ExitCode)"}
    Copy-Item -LiteralPath "$project/Binaries/Win64/UnrealEditor.modules" -Destination "$out/Module/UnrealEditor.modules"
    @{editor_compile=$compile.ExitCode;isolated_link=$link.ExitCode;active_editor_untouched=$true;
        module_sha256=(Get-FileHash -LiteralPath "$out/Module/UnrealEditor-FPSGAME.dll").Hash;finished=(Get-Date).ToString('o')} |
        ConvertTo-Json | Set-Content -LiteralPath "$out/Editor-build.json" -Encoding utf8
    Write-Output "HILLS_REVIEW_MODULE=$out/Module/UnrealEditor-FPSGAME.dll"
    if($EditorOnly){return}
    $gameCommand='""E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat" FPSGAME Win64 Development "-Project='+$project+'/FPSGAME.uproject" -gather -NoHotReload -NoHotReloadFromIDE -NoUBA -NoUBALocal -NoXGE -NoSNDBS -NoFASTBuild -MaxParallelActions=4 "-Log='+$out+'/Logs/Game-build.log""'
    $game=Start-Process -FilePath $env:ComSpec -ArgumentList @('/d','/s','/c',$gameCommand) -WindowStyle Hidden -PassThru -RedirectStandardOutput "$out/Logs/Game-stdout.log" -RedirectStandardError "$out/Logs/Game-stderr.log"
    Wait-OwnBuild $game
    @{exit_code=$game.ExitCode;finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath "$out/Game-build.json" -Encoding utf8
    if($game.ExitCode -ne 0){throw "Game build failed: $($game.ExitCode)"}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
