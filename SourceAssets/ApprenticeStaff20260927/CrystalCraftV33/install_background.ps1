param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8',[switch]$Resume)
$ErrorActionPreference='Stop'
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue) {
    throw 'An Unreal process is running. Use the existing editor mutex bridge; no process was stopped.'
}
$resumeArg=if($Resume){'-CrystalCraftResume'}else{'-CrystalCraftFresh'}
& "$EngineRoot/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" "$projectRoot/FPSGAME.uproject" `
    -run=pythonscript "-script=$PSScriptRoot/install_ue.py" -AllowCommandletRendering -d3d12 `
    -unattended -nop4 -nosplash -nosound -RenderOffscreen $resumeArg `
    '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' `
    "-abslog=$PSScriptRoot/import-commandlet.log" *> "$PSScriptRoot/import-console.log"
if($LASTEXITCODE -ne 0) {throw "Crystal production failed: $LASTEXITCODE. See import-commandlet.log."}
