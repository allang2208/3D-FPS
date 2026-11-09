param([string]$Label='before',[switch]$Arms,[switch]$Side)
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'Render batch wait expired'}
    $log="$project/Saved/Logs/M249_Repair03_optics_$Label.log"
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    [string[]]$selection=if($Arms){@('-M249')}else{@("-SurfaceManifest=$PSScriptRoot/optic_surface_manifest.json")}
    if($Side){$selection+='-M249Side'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" -run=M24HoldReview @selection "-Output=$PSScriptRoot/UEOptics_$Label" -RenderOffscreen -AllowCommandletRendering -unattended -NoSound -NoP4 "-abslog=$log" *> "$log.console"
    $code=$LASTEXITCODE
    Get-Content -LiteralPath $log -Tail 4
    if($code -ne 0){throw "M249 optical capture exit $code"}
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
