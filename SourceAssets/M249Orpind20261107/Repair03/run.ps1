param([string]$Script='import.py',[switch]$Render)
$ErrorActionPreference='Stop'
$project=(Resolve-Path "$PSScriptRoot/../../..").Path
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'UE batch wait expired'}
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {($_.CommandLine -replace '\\','/') -like '*D:/FPS3D/FPSGAME/FPSGAME.uproject*'})
    if($editors.Count){
        $stamp=Get-Date -Format 'yyyyMMdd_HHmmssfff'
        & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript "$PSScriptRoot/$Script" -OutputFile "$project/Saved/M249ReloadReview/Repair03_$Script.$stamp.bridge.txt"
        if(!$?){throw 'Existing editor import failed'}
    }else{
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $log="$project/Saved/Logs/M249_Repair03_$Script.log"
        [string[]]$rhi=if($Render){@('-RenderOffscreen','-AllowCommandletRendering')}else{@('-NullRHI')}
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" -run=pythonscript "-script=$PSScriptRoot/$Script" -unattended @rhi -NoSound -NoP4 "-abslog=$log" *> "$log.console"
        $code=$LASTEXITCODE
        Get-Content -LiteralPath $log -Tail 6
        if($code -ne 0){throw "M249 commandlet exit $code"}
    }
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
