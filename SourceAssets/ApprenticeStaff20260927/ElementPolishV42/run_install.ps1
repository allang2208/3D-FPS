$ErrorActionPreference='Stop'
$taskProject=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$taskScript=Join-Path $PSScriptRoot 'install_ue.py'
$taskStamp=[DateTime]::Now.ToString('yyyyMMdd-HHmmss')
$taskDeadline=[DateTime]::UtcNow.AddMinutes(15)
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
$taskNotified=$false
try {
    while(-not $taskHeld) {
        if([DateTime]::UtcNow -gt $taskDeadline){throw 'The asset execution window stayed occupied; production files preserved.'}
        if(Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
            & (Join-Path $taskProject 'Tools/AssetPipeline/mcp_call_codex.ps1') -PythonScript $taskScript `
                -OutputFile (Join-Path $PSScriptRoot "install-$taskStamp-bridge.txt") -MaxOutputChars 2200 -QueueWaitSeconds 300 -RequestTimeoutSeconds 180
            if($LASTEXITCODE -ne 0){throw 'ELEMENT_POLISH_V42 existing-editor installation did not complete.'}
            exit 0
        }
        $taskBusy=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^(UnrealBuildTool|cl|link|UnrealEditor-Cmd)\.exe$' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        if($taskBusy) {
            if(-not $taskNotified){Write-Output 'Waiting for the current background asset/build process.';$taskNotified=$true}
            Start-Sleep -Seconds 10
            continue
        }
        try {$taskHeld=$taskGate.WaitOne(1000)}
        catch [Threading.AbandonedMutexException] {$taskHeld=$true}
    }
    if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An editor process appeared before launch; no overlapping import was started.'}
    $taskLog=Join-Path $PSScriptRoot "install-$taskStamp-commandlet.log"
    $taskStdout=Join-Path $PSScriptRoot "install-$taskStamp-console.log"
    Write-Output 'Starting the ELEMENT_POLISH_V42 D3D12 asset commandlet.'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" `
        -run=pythonscript "-script=$taskScript" -AllowCommandletRendering -d3d12 `
        -unattended -nop4 -nosplash -nosound -RenderOffscreen -multiprocess -stdout `
        '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
        "-abslog=$taskLog" *> $taskStdout
    if($LASTEXITCODE -ne 0){throw "ELEMENT_POLISH_V42 commandlet failed ($LASTEXITCODE); see $taskLog"}
    Write-Output "ELEMENT_POLISH_V42_ASSET_COMMANDLET_FINISHED $taskLog"
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
