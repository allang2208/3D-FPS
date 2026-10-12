param([string]$Name='wheel-before',[switch]$ReopenAfterMissingIcon)
$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $held=$gate.WaitOne([TimeSpan]::FromSeconds(60))
    if(-not $held){throw 'UE batch gate occupied.'}
    $active=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor(?:-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME[\\/]FPSGAME\.uproject'
    })
    # A finishing background commandlet may not hold the bridge gate; wait without stopping it.
    if($active.Count -and -not ($active | Where-Object {$_.Name -eq 'UnrealEditor.exe'})) {
        foreach($job in $active){Wait-Process -Id $job.ProcessId -Timeout 55 -ErrorAction SilentlyContinue}
        $active=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -match '^UnrealEditor(?:-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME[\\/]FPSGAME\.uproject'
        })
    }
    if($active.Count){throw 'An editor or commandlet is active. No process was stopped.'}
    $dest=Join-Path $root 'Saved/ShotgunAmmoModels20261012'
    New-Item -ItemType Directory -Path $dest -Force | Out-Null
    $extra=@(if($ReopenAfterMissingIcon){'-ReopenAfterMissingIcon'})
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$root/FPSGAME.uproject" `
      -run=ShotgunAmmoIconDiagnosis -AllowCommandletRendering -RenderOffscreen -unattended -nop4 -nosplash -nosound `
      "-Output=$dest/$Name.png" "-abslog=$dest/$Name.log" @extra *> "$dest/$Name.stdout.log"
    $result=$LASTEXITCODE
    Select-String -LiteralPath "$dest/$Name.log" -Pattern 'AMMO_ICON_DIAG|Error:|Fatal' | ForEach-Object {$_.Line}
    if($result){throw "Wheel diagnosis exited $result"}
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
