param([string]$Engine='E:/Program Files (x86)/UE_5.8',
      [string]$Batch='F:/FPSGAMEData/ArtProduction/HillsVillageWindmill/MillKeeperR1',
      [switch]$DialogueOnly, [switch]$WardrobeOnly)
$ErrorActionPreference='Stop'
$project=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$assembly=Join-Path $project 'SourceAssets/HillsVillageWindmill/MillKeeper/CharacterR1/Assembly'
$receipt=Join-Path $assembly 'saved.json'
$scriptPath=Join-Path $PSScriptRoot 'import_keeper.py'
if ($WardrobeOnly -and $DialogueOnly) { throw 'Choose one keeper import mode.' }
if ($WardrobeOnly) {
    $receipt=Join-Path $assembly 'outfit_workwear_r4.json'
    $scriptPath=Join-Path $PSScriptRoot 'update_keeper_outfit.py'
    if (!$PSBoundParameters.ContainsKey('Batch')) {
        $Batch=Join-Path (Split-Path -Parent $Batch) ('MillKeeperWorkwearR4/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    }
}
if ($DialogueOnly) {
    $receipt=Join-Path $assembly 'dialogue_r1.json'
    $scriptPath=Join-Path $PSScriptRoot 'connect_keeper_dialogue.py'
    if (!$PSBoundParameters.ContainsKey('Batch')) {
        $Batch=Join-Path (Split-Path -Parent $Batch) ('MillKeeperDialogueR1/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
    }
}
$start=[DateTime]::UtcNow
New-Item -ItemType Directory -Force -Path $Batch | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    $editor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {
        $_.CommandLine.Replace('\','/').Contains($project.Replace('\','/')+'/FPSGAME.uproject') -or !$_.CommandLine.Contains('.uproject')
    })
    if ($editor.Count) {
        $gate.ReleaseMutex(); $held=$false
        & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $scriptPath -OutputFile "$Batch/bridge.json" -QueueWaitSeconds 300
    } else {
        & "$Engine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$project/FPSGAME.uproject" /Engine/Maps/Entry -run=pythonscript "-script=$scriptPath" -unattended -NullRHI -nop4 -nosplash -nosound -Multiprocess -AssetGatherAll=false -asyncskinnedassetcompilation=0 -asynctexturecompilation=0 '-ini:Engine:[ConsoleVariables]:Interchange.FeatureFlags.Import.FBX=False' "-abslog=$Batch/import.log" > "$Batch/console.log" 2>&1
    }
    if (!(Test-Path $receipt) -or (Get-Item $receipt).LastWriteTimeUtc -lt $start) {
        throw "Keeper import incomplete. See $Batch"
    }
} finally {if ($held){$gate.ReleaseMutex()}; $gate.Dispose()}
