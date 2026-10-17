$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){throw 'The shared UE build batch is occupied.'}
    $deadline=[DateTime]::UtcNow.AddMinutes(30)
    while($true) {
        $busy=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('cl.exe','link.exe')
        })
        if(-not $busy.Count){break}
        if([DateTime]::UtcNow -gt $deadline){throw 'Existing native build did not finish.'}
        Start-Sleep -Seconds 5
    }
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development '-Project=D:/FPS3D/FPSGAME/FPSGAME.uproject' -WaitMutex -NoHotReload -NoHotReloadFromIDE -NoUBTMakefiles ("-Log="+(Join-Path $PSScriptRoot 'build_game_engine.log')) *> (Join-Path $PSScriptRoot 'build_game.log')
    $code=$LASTEXITCODE
    [ordered]@{target='FPSGAME Win64 Development';exit_code=$code;completed=($code -eq 0)} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'build_game_receipt.json') -Encoding utf8
    if($code -ne 0){throw 'M870 standalone Game build failed.'}
    Write-Output 'M870 standalone Game target built.'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
