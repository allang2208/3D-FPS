param([string]$ScriptName = 'save_assets.py', [int]$MaxMinutes = 180)
# Retry only failures that guarantee nothing was written: PIE running, gate or
# project busy. Any other failure stops so nothing is replayed blindly.
$ErrorActionPreference = 'Stop'
$deadline = (Get-Date).AddMinutes($MaxMinutes)
$stem = [IO.Path]::GetFileNameWithoutExtension($ScriptName)
$reported = @{}
while ((Get-Date) -lt $deadline) {
    $before = Get-Date
    try {
        & (Join-Path $PSScriptRoot 'run_when_idle.ps1') -ScriptName $ScriptName
        Write-Output "$ScriptName finished."
        return
    } catch {
        $message = $_.Exception.Message
        $result = Get-ChildItem $PSScriptRoot -Filter "bridge-$stem-*.txt" | Where-Object { $_.LastWriteTime -ge $before } |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        # An empty bridge result means the client never reached an editor host. A
        # partial save cannot be replayed: save_assets.py only accepts the two known hashes.
        $reason = if ($message -match 'no asset write started|no commandlet started') { 'busy' }
            elseif ($result -and $result.Length -eq 0) { 'bridge' }
            elseif ($result -and (Select-String -LiteralPath $result.FullName -Pattern 'PIE active; no assets changed|Preserve unsaved targets' -Quiet)) { 'pie' }
            else { $null }
        if (-not $reason) { throw }
        if ($result) { Remove-Item -LiteralPath $result.FullName }
        if (-not $reported[$reason]) { Write-Output "Deferred ($reason); no asset changed, retrying."; $reported[$reason] = $true }
        Start-Sleep -Seconds 60
    }
}
throw 'Still deferred at the deadline; no asset write started.'
