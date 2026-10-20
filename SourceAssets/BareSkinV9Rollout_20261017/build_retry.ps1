param([int]$MaxWaitMinutes = 240, [int]$RetrySeconds = 300)
# Builds Editor then Game. If a build fails only on files another session is still editing, waits and retries;
# stops at once if any error is in this task's own sources.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot; $deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
$own = 'FPSArmJointCorrectiveComponent|FPSGAMECharacter\.cpp'
foreach ($target in 'FPSGAMEEditor', 'FPSGAME') {
    while ($true) {
        $ErrorActionPreference = 'Continue'
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $here 'build_native.ps1') -Targets $target *> $null
        $ErrorActionPreference = 'Stop'
        $log = Get-ChildItem $here -Filter "build-$target-*.log" | Sort-Object LastWriteTime | Select-Object -Last 1
        if (Select-String -Path $log.FullName -Pattern 'Result: Succeeded' -Quiet) { Write-Output "$target succeeded ($($log.Name))"; break }
        $errors = Select-String -Path $log.FullName -Pattern 'error C|error LNK|: error' | ForEach-Object Line
        if ($errors | Where-Object { $_ -match $own }) { throw "$target failed in this task's sources: $($log.FullName)" }
        if ((Get-Date) -gt $deadline) { throw "$target still blocked by other sessions' sources: $($log.FullName)" }
        $files = ($errors | ForEach-Object { if ($_ -match '([A-Za-z0-9_]+\.(h|cpp))\(') { $Matches[1] } } | Sort-Object -Unique) -join ', '
        Write-Output "$target blocked by other in-progress sources ($files); retry in $RetrySeconds s"
        Start-Sleep -Seconds $RetrySeconds
    }
}
Write-Output 'M4V9_BUILDS_COMPLETE'

