$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $deadline=[DateTime]::UtcNow.AddMinutes(20)
    while(-not $held) {
        if([DateTime]::UtcNow -gt $deadline){throw 'Existing build/asset batch did not finish; no duplicate build started.'}
        $busy=@(Get-CimInstance Win32_Process -Filter "Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('cl.exe','link.exe','UnrealEditor-Cmd.exe')})
        if($busy.Count){Start-Sleep -Seconds 5;continue}
        try {$held=$gate.WaitOne(1000)} catch [Threading.AbandonedMutexException] {$held=$true}
    }
    & 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1'
    if($LASTEXITCODE -ne 0){throw 'M870 third-person build did not succeed.'}
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
