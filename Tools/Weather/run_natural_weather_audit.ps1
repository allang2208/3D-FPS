param(
    [ValidateSet('DayNight_Lighting','L_Normandy_FPS_Test','L_MilitaryTrench_FPS_Test')]
    [string]$Map='DayNight_Lighting',
    [string]$Label='DayNight-final',
    [ValidateSet('Presentation','Storm','Panel')][string]$Mode='Presentation',
    [switch]$Sequence
)
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$outputPath = Join-Path $projectRoot ('Saved/WeatherPresentation20260912/'+$Label)
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
$editorPath = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe'
$arguments = @(
    ('"'+$projectRoot+'/FPSGAME.uproject"'),('/Game/GameMaps/'+$Map),
    '-game','-windowed','-ResX=1280','-ResY=720','-RenderOffscreen','-unattended','-nosound','-nosplash',
    ('-'+@{Presentation='WeatherPresentationAudit';Storm='StormCloudAudit';Panel='WeatherPanelAudit'}[$Mode]),('-WeatherAuditLabel='+$Label),('-ColdSteelProfile=Weather_'+$Label),
    ('-abslog="'+$outputPath+'/runtime.log"')
)
if($Sequence){$arguments+='-WeatherCaptureSequence'}
$auditProcess=Start-Process -FilePath $editorPath -ArgumentList $arguments -WindowStyle Hidden -PassThru
$auditProcess.Id | Set-Content -LiteralPath (Join-Path $outputPath 'process-id.txt')
$auditProcess.WaitForExit()
$log=Get-Content -LiteralPath (Join-Path $outputPath 'runtime.log')
$log | Select-String 'WEATHER_PRESENTATION_CHECK|WEATHER_PRESENTATION_AUDIT_|STORM_CLOUD_AUDIT_|STORM_GPU|WEATHER_PANEL_AUDIT_|WeatherPresentation ready|Failed to compile Material|LogNiagara: Error|Fatal error|Assertion failed'
$marker=@{Presentation='WEATHER_PRESENTATION_AUDIT_PASS';Storm='STORM_CLOUD_AUDIT_PASS';Panel='WEATHER_PANEL_AUDIT_PASS'}[$Mode]
if(-not ($log -match $marker)){exit 1}
if($log -match 'Failed to compile Material|Fatal error|Assertion failed'){exit 2}
exit $auditProcess.ExitCode
