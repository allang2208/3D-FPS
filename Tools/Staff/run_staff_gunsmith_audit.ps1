param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
    throw 'An Unreal process is running. No process was stopped; close it before this explicit headless audit.'
}
$out=Join-Path $projectRoot 'Saved/StaffGunsmith'
New-Item -ItemType Directory -Path $out -Force | Out-Null
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$projectRoot/FPSGAME.uproject" `
    -run=StaffGunsmithAudit -unattended -nop4 -nosplash -nosound -nullrhi `
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
    "-abslog=$out/commandlet.log" *> "$out/console.log"
if($LASTEXITCODE -ne 0) {throw "Staff gunsmith audit failed: $LASTEXITCODE. See $out/commandlet.log."}
Get-Content (Join-Path $out 'transaction-report.txt')
