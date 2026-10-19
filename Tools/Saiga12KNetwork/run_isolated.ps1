param([string]$Stage='before',[switch]$SkipBuild,[switch]$Presentation)
$ErrorActionPreference='Stop'
$s12Root='D:/FPS3D/FPSGAME'
$s12Out="$s12Root/SourceAssets/Saiga12KNetwork20261019/Receipts/$Stage"
New-Item -ItemType Directory -Force -Path $s12Out | Out-Null
$s12Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$s12Held=$false
try {
    try {$s12Held=$s12Gate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$s12Held=$true;throw 'Abandoned UE batch; preserve state.'}
    if(-not $s12Held){throw 'Shared UE batch remained busy.'}
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue){throw 'Interactive editor is open; preserve it.'}
    $s12Deadline=(Get-Date).AddMinutes(10)
    do {
        $s12Busy=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealBuildTool.exe' -or ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -like '*FPSGAME.uproject*') })
        if($s12Busy.Count){if((Get-Date) -gt $s12Deadline){throw 'Existing project process remained busy.'};Start-Sleep -Seconds 5}
    } while($s12Busy.Count)
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    if(-not $SkipBuild){
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$s12Root/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -NoUBTMakefiles -MaxParallelActions=4 -WaitMutex "-Log=$s12Out/build-editor.log" *> "$s12Out/build-editor-console.log"
        $s12Code=$LASTEXITCODE
        @{target='FPSGAMEEditor';exit_code=$s12Code;completed=(Get-Date).ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath "$s12Out/build.json" -Encoding utf8
        if($s12Code -ne 0){throw "Editor build failed: $s12Code"}
    }
    $s12Mode=if($Presentation){'-Saiga12KPresentation'}else{'-Saiga12KNetwork'}
    $s12PresentationResult="$s12Root/Saved/Saiga12KThirdPerson20261018/result.json"
    if($Presentation -and (Test-Path -LiteralPath $s12PresentationResult)){Copy-Item -LiteralPath $s12PresentationResult -Destination "$s12Out/previous-result.json"}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$s12Root/FPSGAME.uproject" -run=ShotgunAttachmentAudit $s12Mode "-Output=$s12Out/result.json" -nullrhi -nosound -unattended -nop4 -nosplash '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' "-abslog=$s12Out/engine.log" *> "$s12Out/console.log"
    $s12Code=$LASTEXITCODE
    if($Presentation -and (Test-Path -LiteralPath $s12PresentationResult)){Copy-Item -LiteralPath $s12PresentationResult -Destination "$s12Out/result.json"}
    @{exit_code=$s12Code;completed=(Get-Date).ToString('o');dll_sha256=(Get-FileHash "$s12Root/Binaries/Win64/UnrealEditor-FPSGAME.dll").Hash;result="$s12Out/result.json"}|ConvertTo-Json|Set-Content -LiteralPath "$s12Out/receipt.json" -Encoding utf8
    Write-Output "S12K_ISOLATED_FINISHED $Stage exit=$s12Code"
    exit $s12Code
} finally {if($s12Held){$s12Gate.ReleaseMutex()};$s12Gate.Dispose()}
