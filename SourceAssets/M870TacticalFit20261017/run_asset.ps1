param([string]$Script='read_inputs.py')
$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$deadline=[DateTime]::UtcNow.AddMinutes(30)
try {
    # Join the existing authoring queue before waiting for external compilers;
    # repeated short batches should not starve this operation between polls.
    Write-Output 'Waiting for the existing UE asset batch gate.'
    while(-not $held) {
        if([DateTime]::UtcNow -gt $deadline){throw 'UE asset batch gate is still occupied.'}
        try {$held=$gate.WaitOne(60000)} catch [Threading.AbandonedMutexException] {$held=$true}
    }
    Write-Output 'Asset gate acquired; waiting for active compilers and commandlets.'
    while($true) {
        $busy=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('cl.exe','link.exe') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -notmatch '(?:^|\s)-game(?:\s|$)')
        })
        if(-not $busy.Count){break}
        if([DateTime]::UtcNow -gt $deadline){throw 'Existing build or commandlet has not finished.'}
        Start-Sleep -Seconds 5
    }
    $editor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject' -and $_.CommandLine -notmatch '(?:^|\s)-game(?:\s|$)'})
    if($editor.Count) {
        & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript (Join-Path $PSScriptRoot $Script) -QueueWaitSeconds 600 -RequestTimeoutSeconds 900 -OutputFile (Join-Path $PSScriptRoot ($Script+'.bridge.txt')) -MaxOutputChars 1500
    } else {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript ("-script="+(Join-Path $PSScriptRoot $Script)) -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen ("-abslog="+(Join-Path $PSScriptRoot ($Script+'.log')))
        if($LASTEXITCODE -ne 0){throw "M870 asset operation failed: $Script"}
    }
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
