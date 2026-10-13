param([int]$WaitBuildProcessId=0)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$outDir=Join-Path $projectRoot 'SourceAssets/Super90CommonStocks20261013'
if($WaitBuildProcessId -gt 0){
    $pending=Get-Process -Id $WaitBuildProcessId -ErrorAction SilentlyContinue
    if($pending){Write-Output 'Waiting for the active native build to finish.';$pending.WaitForExit()}
}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $held=$gate.WaitOne([TimeSpan]::FromSeconds(60))
    if(-not $held){throw 'UE batch gate occupied; no import was started.'}
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {$_.CommandLine -match 'FPSGAME.uproject'})
    if($editors.Count){throw 'FPSGAME is active; preserve its packages and use the existing bridge.'}
    $builds=@(Get-CimInstance Win32_Process | Where-Object {($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('cl.exe','UnrealBuildTool.exe')})
    if($builds.Count){throw 'Another build started; preserve its link window.'}
    $engine='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $arguments=@((Join-Path $projectRoot 'FPSGAME.uproject'),'-run=pythonscript',('-script='+$outDir+'/install.py'),'-unattended','-nosplash','-AllowCommandletRendering','-RenderOffscreen',('-abslog='+$outDir+'/install.log'))
    & $engine @arguments *> (Join-Path $outDir 'install-console.txt')
    if($LASTEXITCODE -ne 0){throw "Stock commandlet failed: $LASTEXITCODE"}
    $receipt=Get-Content -LiteralPath (Join-Path $outDir 'install_receipt.json') -Raw | ConvertFrom-Json
    if(-not $receipt.complete){throw 'Stock commandlet did not finish saving its assets.'}
    Write-Output 'Five stock assemblies and native factory sections saved.'
    & (Join-Path $projectRoot 'Tools/Build/Build-Editor.ps1') *> (Join-Path $outDir 'build-final-console.txt')
    Get-Content -LiteralPath (Join-Path $outDir 'build-final-console.txt') -Tail 8
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
