param([string]$Label='before',[switch]$UserEquipment,[switch]$CachedASH12)
$ErrorActionPreference='Stop'
while($quickBuilds=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
    foreach($quickBuild in $quickBuilds) { try { Wait-Process -Id $quickBuild.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { } }
}
$quickGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$quickHeld=$false
try {
    $quickHeld=$quickGate.WaitOne([TimeSpan]::FromSeconds(300))
    if(-not $quickHeld){throw 'UE batch remains busy'}
    if(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'UnrealEditor.exe' -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME') }) {throw 'Preserve active editor or project commandlet'}
    $quickExtra=@();if($UserEquipment){$quickExtra+='-UserEquipment'};if($CachedASH12){$quickExtra+='-CachedASH12'}
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' `
        -run=WarhammerSprintAudit -QuickCombatOnly @quickExtra ('-Report='+(Join-Path $PSScriptRoot ($Label+'-trace.txt'))) `
        -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile `
        '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
        ('-abslog='+(Join-Path $PSScriptRoot ($Label+'-engine.log'))) -stdout -FullStdOutLogOutput *> (Join-Path $PSScriptRoot ($Label+'-console.log'))
    $quickExit=$LASTEXITCODE
    @{exit_code=$quickExit;finished=(Get-Date).ToString('s')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot ($Label+'-receipt.json')) -Encoding utf8
    if(Test-Path -LiteralPath (Join-Path $PSScriptRoot ($Label+'-trace.txt'))) { Get-Content -LiteralPath (Join-Path $PSScriptRoot ($Label+'-trace.txt')) -Head 8; Get-Content -LiteralPath (Join-Path $PSScriptRoot ($Label+'-trace.txt')) -Tail 1 }
    else {Get-Content -LiteralPath (Join-Path $PSScriptRoot ($Label+'-console.log')) -Tail 12}
    exit $quickExit
} finally {if($quickHeld){$quickGate.ReleaseMutex()};$quickGate.Dispose()}
