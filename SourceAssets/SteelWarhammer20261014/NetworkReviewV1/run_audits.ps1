$ErrorActionPreference='Stop'
$reviewProject='D:\FPS3D\FPSGAME\FPSGAME.uproject'
while($reviewBusy=@(Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
    ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME' -and $_.CommandLine -notmatch '(?i)(?:^|\s)-game(?:\s|$)')
})) {
    foreach($reviewProcess in $reviewBusy) {
        Write-Output ('Waiting for process '+$reviewProcess.ProcessId)
        try {Wait-Process -Id $reviewProcess.ProcessId -ErrorAction Stop} catch [Microsoft.PowerShell.Commands.ProcessCommandException] {}
    }
}
$reviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$reviewHeld=$false
$reviewResults=@()
try {
    $reviewHeld=$reviewGate.WaitOne([TimeSpan]::FromSeconds(300))
    if(-not $reviewHeld){throw 'Asset batch busy; no commandlet started.'}
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'"){throw 'Preserve open editor; defer isolated audit commandlet.'}
    foreach($reviewName in @('WarhammerNetworkAudit','WarhammerModificationAudit')) {
        $reviewLog=Join-Path $PSScriptRoot ($reviewName+'.log')
        $reviewReport=Join-Path $PSScriptRoot ($reviewName+'.json')
        & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $reviewProject `
            ('-run='+$reviewName) ('-Out='+$reviewReport) -unattended -nop4 -nosplash -nullrhi -nosound -NoShaderCompile `
            '-ini:Engine:[/Script/PythonScriptPlugin.PythonScriptPluginSettings]:bRemoteExecution=False' `
            ('-abslog='+$reviewLog) -stdout -FullStdOutLogOutput *> (Join-Path $PSScriptRoot ($reviewName+'-console.log'))
        $reviewCode=$LASTEXITCODE
        $reviewResults+=@{name=$reviewName;exit_code=$reviewCode;report=$reviewReport;log=$reviewLog}
        $reviewResults | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'audit_receipt.json') -Encoding utf8
        Write-Output ($reviewName+' exit='+$reviewCode)
        Select-String -LiteralPath $reviewLog -Pattern 'HAMMER_NETWORK (FAIL)|HAMMER_NETWORK_DONE|HAMMER_MODS (FAIL)|HAMMER_MODS_DONE|Fatal error' | ForEach-Object {$_.Line}
    }
} finally {
    if($reviewHeld){$reviewGate.ReleaseMutex()}
    $reviewGate.Dispose()
}
if($reviewResults.Where({$_.exit_code -ne 0}).Count -gt 0){exit 1}
