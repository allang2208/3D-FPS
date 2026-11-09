param([string]$Label='before',[string]$View='left',[string]$Times='0,0.18,0.36,0.45,0.48,0.54,0.66,0.72',[switch]$Retract)
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'Review batch wait expired'}
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {($_.CommandLine -replace '\\','/') -like '*D:/FPS3D/FPSGAME/FPSGAME.uproject*'})
    if($editors.Count){throw 'Existing editor retained; use its bridge for review instead of a second asset host'}
    $direction=if($Retract){'retract'}else{'deploy'}
    $extra=if($Retract){'-Retract'}else{''};$sequence=$Times.Replace(',','|')
    $log="$project/Saved/Logs/M249Repair10_${Label}_${View}_${direction}.log"
    $arguments='"{0}/FPSGAME.uproject" -run=M24HoldReview -M249 -M249Focus -Role=bipod -View={1} -Times={2} {3} -Output="{4}/{5}_{1}_{6}" -RenderOffscreen -AllowCommandletRendering -unattended -NoSound -NoP4 -abslog="{7}"' -f $project,$View,$sequence,$extra,$PSScriptRoot,$Label,$direction,$log
    $process=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait -RedirectStandardOutput "$log.console" -RedirectStandardError "$log.stderr"
    $code=$process.ExitCode
    Get-Content -LiteralPath $log -Tail 5
    if($code -ne 0){throw "Bipod native review exit $code"}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
