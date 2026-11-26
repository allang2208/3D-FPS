# Exercise the local hills save and player inputs in an isolated offscreen game.
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$out = Join-Path $project ('Saved/RainforestBankCheck/' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$saves = Join-Path $out 'Saved/SaveGames'
[void](New-Item -ItemType Directory -Force -Path $saves)
Copy-Item -LiteralPath (Join-Path $project 'Saved/SaveGames/TemperateHills_World.sav') -Destination $saves
$intermediate = Join-Path $out 'Intermediate'
[void](New-Item -ItemType Directory -Force -Path $intermediate)
foreach ($name in 'CachedAssetRegistry','CachedAssetRegistryDiscovery.bin') {
    $source = Join-Path $project "Intermediate/$name"
    if (Test-Path -LiteralPath $source) {Copy-Item -LiteralPath $source -Destination $intermediate -Recurse}
}
$testArgs = @(
    ('"' + (Join-Path $project 'FPSGAME.uproject') + '"'), '/Game/GameMaps/L_TemperateHills_Initial',
    '-game', '-RenderOffscreen', '-windowed', '-ResX=1280', '-ResY=720', '-unattended', '-nosound',
    '-nosplash', '-ClearwaterNoMenu', '-SkipStartupMenu', '-RainforestBankCheck', '-ColdSteelProfile=RainforestBankCheck',
    ('-UserDir="' + $out + '"'), ('-abslog="' + (Join-Path $out 'bank.log') + '"'),
    '-ExecCmds="t.MaxFPS 45,fps.Test.RainforestBank"',
    '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False',
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False'
)
$exe = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$previousSdkSetting = $env:UE_SKIP_UBT_SDK_SETUP
try {
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    $testProcess = Start-Process -FilePath $exe -ArgumentList $testArgs -WindowStyle Hidden -PassThru
} finally {
    $env:UE_SKIP_UBT_SDK_SETUP = $previousSdkSetting
}
Write-Output "Rainforest bank run $($testProcess.Id): $out"
if (!$testProcess.WaitForExit(600000)) {
    $testProcess.Kill()
    throw "Runtime timed out. See $out/bank.log"
}
$testProcess.Refresh()
Get-Content -LiteralPath (Join-Path $out 'bank.log') -Encoding utf8 | Select-String 'BANK_|HILLS_FOREST_LANDED'
exit $testProcess.ExitCode
