param([switch]$KilnSurfacesOnly)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$stage = Join-Path $root 'Saved/VillageTavern/ServiceHost'
$content = Join-Path $stage 'Content'
New-Item -ItemType Directory -Force -Path $content,"$stage/Config" | Out-Null
'[ConsoleVariables]', 'Interchange.FeatureFlags.Import.FBX=0' | Set-Content -LiteralPath "$stage/Config/DefaultEngine.ini" -Encoding utf8
$hostFile = Join-Path $stage 'TaproomService.uproject'
@{FileVersion=3; EngineAssociation='5.8'; Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})} |
    ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $hostFile -Encoding utf8
foreach ($relative in 'WorldGeneration/TemperateHills','UnrealNormandy/Textures','WorldGeneration/VillageTavern/Service') {
    $target = Join-Path "$root/Content" $relative
    $link = Join-Path $content $relative
    New-Item -ItemType Directory -Force -Path $target,(Split-Path -Parent $link) | Out-Null
    if (!(Test-Path -LiteralPath $link)) { New-Item -ItemType Junction -Path $link -Target $target | Out-Null }
}
$gate = [Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne() } catch [Threading.AbandonedMutexException] { $held=$true }
    $ue = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $script = if ($KilnSurfacesOnly) {'import_kiln_textures.py'} else {'import_service.py'}
    $marker = if ($KilnSurfacesOnly) {'TAVERN_KILN_SURFACES_SAVED'} else {'TAVERN_SERVICE_SAVED'}
    $log = Join-Path $stage ($script + '.log')
    & $ue $hostFile -run=pythonscript "-script=$PSScriptRoot/$script" -unattended -nop4 -nosplash -nosound -NullRHI -Multiprocess -AssetGatherAll=false -NoAssetRegistryCacheWrite '-ExecCmds=Interchange.FeatureFlags.Import.FBX 0' "-abslog=$log" *> "$stage/Console.log"
    if ($LASTEXITCODE -ne 0 -or !(Select-String -LiteralPath $log -SimpleMatch $marker -Quiet)) { throw "Taproom service import failed. See $log" }
    Write-Output $marker
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
