param([string]$Label='before',[string]$Role='idle',[string]$View='ads',[string]$Times='0')
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'M249 review batch wait expired'}
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    $log="$project/Saved/Logs/M249_Repair06_${Label}_${Role}_${View}.log"
    # The existing commandlet's FParse stops at commas. Dispatch single times
    # so each requested sample is rendered even with that installed binary.
    $rows=@()
    foreach($sample in $Times.Split(',')){
        $args='"{0}/FPSGAME.uproject" -run=M24HoldReview -M249 -M249Focus -Role={1} -View={2} -Times={3} -Output="{4}/{5}_{1}_{2}" -RenderOffscreen -AllowCommandletRendering -unattended -NoSound -NoP4 -abslog="{6}"' -f $project,$Role,$View,$sample,$PSScriptRoot,$Label,$log
        $process=Start-Process -FilePath 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' -ArgumentList $args -WindowStyle Hidden -PassThru -RedirectStandardOutput "$log.console" -RedirectStandardError "$log.stderr"
        $process.WaitForExit();$code=$process.ExitCode
        Get-Content -LiteralPath $log -Tail 4
        if($code -ne 0){throw "M249 review exit $code"}
        $reportPath="$PSScriptRoot/${Label}_${Role}_${View}/review.json"
        $report=Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
        $rows+=@($report.views)
    }
    $report.views=$rows
    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $reportPath -Encoding utf8
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
