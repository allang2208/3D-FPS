$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
$deadline=[DateTime]::UtcNow.AddMinutes(30)
try {
    Write-Output 'Waiting for the shared UE batch gate to build the M870 trigger integration.'
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'The UE batch gate is still occupied.'}
    while($true) {
        $busy=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('cl.exe','link.exe') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -notmatch '(?:^|\s)-game(?:\s|$)')
        })
        if(-not $busy.Count){break}
        if([DateTime]::UtcNow -gt $deadline){throw 'Existing build or commandlet has not finished.'}
        Start-Sleep -Seconds 5
    }
    & 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1' *> (Join-Path $PSScriptRoot 'build_editor.log')
    if($LASTEXITCODE -ne 0){throw 'M870 trigger Editor build failed.'}
    [ordered]@{completed=$true;target='FPSGAMEEditor Win64 Development';runtime_tested=$false} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_receipt.json') -Encoding utf8
    Write-Output 'M870 lightweight trigger integration built.'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
