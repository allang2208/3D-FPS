$ErrorActionPreference='Stop'
$taskProject='D:/FPS3D/FPSGAME'
$label='svch-sights-r2-20261019-a3'
$output=Join-Path $taskProject ('Saved/SVCHPoseAudit/'+$label)
if(Test-Path -LiteralPath $output){throw 'This capture label already exists; keep the original evidence.'}
$argsList=@(
    ('"'+$taskProject+'/FPSGAME.uproject"'),
    '/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation',
    '-game','-windowed','-RenderOffscreen','-ForceRes','-ResX=1600','-ResY=900',
    '-unattended','-nosplash','-nosound','-d3d12','-FixedSeed','-SkipStartupMenu','-DisablePython',
    '-UseFixedTimeStep','-FPS=60','-SVCHPoseAudit','-SVCHSightsOnly','-SVCHBoltFitReview','-SVCHHandoffReview','-SVCHPoseAuditStudio',
    ('-ColdSteelProfile=SVCHPoseAudit_'+$label),('-GunplayLabel='+$label),
    ('-abslog="'+$PSScriptRoot+'/bolt-runtime.log"'))
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(600))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'UE batch gate remained busy; no sight capture was started.'}
    $busy=@(Get-CimInstance Win32_Process | Where-Object {
        $_.Name -in @('cl.exe','link.exe') -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and
            (!$_.CommandLine -or $_.CommandLine.Replace('\','/').IndexOf('D:/FPS3D/FPSGAME/FPSGAME.uproject',[StringComparison]::OrdinalIgnoreCase) -ge 0))
    })
    if($busy.Count){throw 'An existing editor, commandlet or build is active; preserve it.'}
    $process=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $argsList -WindowStyle Hidden -PassThru
    Write-Output "Owned offscreen sight check PID $($process.Id); hip/ADS only; isolated profile."
    $process.WaitForExit()
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
if(!(Test-Path -LiteralPath ($output+'/completion.json'))){throw 'No sight check completion record; retain runtime.log.'}
$result=Get-Content -LiteralPath ($output+'/completion.json') -Raw | ConvertFrom-Json
$result | ConvertTo-Json -Depth 6
if(!$result.completed){exit 1}
