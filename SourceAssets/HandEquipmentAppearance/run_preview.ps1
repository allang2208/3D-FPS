param([Parameter(Mandatory=$true)][string]$Label)
$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
if ($Label -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid label' }
$outputDir=Join-Path $projectRoot ('Saved/GunplayUpgrade/'+$Label)
if (Test-Path -LiteralPath $outputDir) { throw 'Choose a fresh label' }
$logPath=Join-Path $PSScriptRoot ('runtime-'+$Label+'.log')
$arguments=@(
    ('"'+$projectRoot+'/FPSGAME.uproject"'),
    '/Game/Weapons/M4InfimaRigV4/Preview/L_M4RigValidation',
    '-game','-windowed','-RenderOffscreen','-ResX=2560','-ResY=1440','-ForceRes','-unattended','-nosplash',
    '-GunplayAudit',('-ColdSteelProfile='+$Label),('-GunplayLabel='+$Label),'-FixedSeed',
    '-d3d12','-DDC=InstalledNoZenLocalFallback','-ModelContextProtocolPort=18013',('-abslog="'+$logPath+'"'),'-UseFixedTimeStep','-FPS=60'
)
$previewProcess=Start-Process 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $arguments -WindowStyle Hidden -PassThru
Write-Output "Glove cuff high-resolution capture process $($previewProcess.Id)"
$previewProcess.WaitForExit()
$lines=Get-Content -LiteralPath (Join-Path $outputDir 'assertions.log')
$pngBytes=[System.IO.File]::ReadAllBytes((Join-Path $outputDir '07_EmptyReload_Charge.png'))
$actualWidth=[System.Net.IPAddress]::NetworkToHostOrder([BitConverter]::ToInt32($pngBytes,16))
$actualHeight=[System.Net.IPAddress]::NetworkToHostOrder([BitConverter]::ToInt32($pngBytes,20))
$result=[ordered]@{
    label=$Label; process_exit=$previewProcess.ExitCode; width=$actualWidth; height=$actualHeight; rhi='DX12';
    pass=@($lines | Where-Object { $_ -match '^GUNPLAY_ASSERT PASS ' }).Count;
    fail=@($lines | Where-Object { $_ -match '^GUNPLAY_ASSERT FAIL ' }).Count;
    completed=@($lines | Where-Object { $_ -match '^GUNPLAY_ACCEPTANCE_COMPLETE ' }).Count -eq 1;
    note='High-resolution material visual review; fixed simulation 60 Hz, not an FPS benchmark.'
}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputDir 'result.json') -Encoding utf8
$result | ConvertTo-Json
if($previewProcess.ExitCode -ne 0 -or !$result.completed -or $actualWidth -ne 2560 -or $actualHeight -ne 1440){exit 1}
