$ErrorActionPreference='Stop'
$batchRoot=$PSScriptRoot
$deadline=(Get-Date).AddMinutes(30)
$projectPath='D:\FPS3D\FPSGAME\FPSGAME.uproject'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$gateHeld=$false
function Get-ProjectUsers {
    @(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor.*\.exe$' -and $_.CommandLine -and
        $_.CommandLine.Replace('/','\').Contains($projectPath)
    })
}
try {
    while ((Get-Date) -lt $deadline) {
        $users=Get-ProjectUsers
        if ($users.Count -gt 0) {
            Write-Output ('Waiting for active project process(es): '+(($users | ForEach-Object {$_.ProcessId}) -join ','))
            Wait-Process -Id $users.ProcessId -Timeout 50 -ErrorAction SilentlyContinue
            continue
        }
        $gateHeld=$gate.WaitOne([TimeSpan]::FromSeconds(50))
        if (-not $gateHeld) { continue }
        if ((Get-ProjectUsers).Count -gt 0) {
            $gate.ReleaseMutex();$gateHeld=$false
            continue
        }
        python (Join-Path $batchRoot 'publish_staged.py')
        $result=$LASTEXITCODE
        exit $result
    }
    throw 'Publication window still occupied; game assets were not replaced.'
} finally {
    if ($gateHeld) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
