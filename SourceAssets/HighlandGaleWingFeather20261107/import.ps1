param([string]$ScriptName)
$ErrorActionPreference='Stop'
$projectDir='D:/FPS3D/FPSGAME'
$src=Join-Path $PSScriptRoot $ScriptName
$outDir=Join-Path $projectDir 'Saved/GaleFeather'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$stem=[IO.Path]::GetFileNameWithoutExtension($ScriptName)
$tag=Get-Date -Format yyyyMMdd-HHmmss
$log=Join-Path $outDir "$stem-$tag.log"
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds(90))} catch [Threading.AbandonedMutexException] {$held=$true}
    if(!$held){throw 'UE asset queue busy'}
    $live=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object CommandLine -match 'FPSGAME')
    if(!$live.Count){
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$projectDir/FPSGAME.uproject" -run=pythonscript "-script=$src" -NullRHI -Unattended -NoSound -NoSplash -nop4 "-UserDir=$outDir/Profile" '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' "-abslog=$log" *> "$log.console"
        $result=$LASTEXITCODE
        Get-Content -LiteralPath $log -Tail 60 | Select-String 'Error|Traceback|FEATHER_|Success|saved' | Select-Object -Last 12 | ForEach-Object Line
        exit $result
    }
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
& "$projectDir/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $src -RequestTimeoutSeconds 240 -OutputFile $log -MaxOutputChars 2200
exit $LASTEXITCODE
