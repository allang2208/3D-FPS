param([string]$Run='baseline',[string]$Cases='cases.json')
$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$taskOutput=Join-Path $PSScriptRoot $Run
New-Item -ItemType Directory -Path $taskOutput -Force | Out-Null
$taskCases=Join-Path $PSScriptRoot $Cases
$taskProfile='WeaponFlameAudit_'+[Guid]::NewGuid().ToString('N').Substring(0,18)
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$taskHeld=$false
try {
    while(-not $taskHeld){try{$taskHeld=$taskGate.WaitOne(10000)}catch [Threading.AbandonedMutexException]{$taskHeld=$true}}
    $taskExisting=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME'})
    if($taskExisting.Count){throw 'Preserve the existing FPSGAME process; use its shared bridge instead.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$taskProject/FPSGAME.uproject" /Game/GameMaps/DayNight_Lighting -game -RenderOffscreen -unattended -nosplash -nosound -windowed -ResX=1280 -ResY=720 -ForceRes -SkipStartupMenu -WeaponFlameVisualAudit "-ColdSteelProfile=$taskProfile" "-WeaponReviewOutput=$taskOutput" "-WeaponReviewCases=$taskCases" '-ExecCmds=fps.WeaponFlameReview,t.MaxFPS 60,r.MotionBlurQuality 0' '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$taskOutput/runtime.log" *> "$taskOutput/console.log"
    $taskExit=$LASTEXITCODE
    @{exit_code=$taskExit;profile=$taskProfile;output=$taskOutput;cases=$taskCases;offscreen=$true} | ConvertTo-Json | Set-Content -LiteralPath "$taskOutput/process.json" -Encoding utf8
    if($taskExit -ne 0){throw "Weapon flame review exited with $taskExit; see $taskOutput/runtime.log"}
} finally {if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()}
