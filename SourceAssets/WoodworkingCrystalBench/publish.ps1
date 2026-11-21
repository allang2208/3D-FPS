param([string]$InstallBatch)
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$work = Join-Path $project 'Saved/WoodworkingCrystalBench'
$stage = Join-Path $work 'Host'
$run = if($InstallBatch){Join-Path $work $InstallBatch}else{Join-Path $work (Get-Date -Format 'yyyyMMdd-HHmmss-fff')}
$content = Join-Path $stage 'Content'
$rel = 'Building/WoodworkingBenchV6Controls20261013'
$names = @('SM_WoodworkingBench','SM_WoodworkingBenchBody')
$backup = Join-Path $run 'Before'
$source = Join-Path $project 'Content'
$paths = @("$content/$rel","$content/CrystalBenchBaseline",$run,$backup)
$baseline=@{}
if(!$InstallBatch){
New-Item -ItemType Directory -Force -Path $paths | Out-Null
@{
    FileVersion = 3
    EngineAssociation = '5.8'
    Plugins = @(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})
} | ConvertTo-Json -Depth 4 | Set-Content "$stage/CrystalBench.uproject" -Encoding utf8
foreach($folder in @("$rel/Materials",'Building/WorkbenchSurfaces20261108','Building/WoodworkingBenchV4','Building/WoodworkingCrystalBench','Building/ArcaneWorkbenchV6_20261107','WorldGeneration/TemperateHills/VillageCarpenter/Props','WorldGeneration/TemperateHills/OldChapel/Textures','UnrealNormandy/Textures')){
    $p=Join-Path $content $folder
    if(!(Test-Path -LiteralPath $p)){
        New-Item -Force -ItemType Directory -Path (Split-Path $p) | Out-Null
        New-Item -ItemType Junction -Path $p -Target (Join-Path $source $folder) | Out-Null
    }
}
foreach($name in $names){
    $file = "$name.uasset"
    Copy-Item -LiteralPath "$source/$rel/$file" -Destination "$backup/$file"
    Copy-Item -LiteralPath "$backup/$file" -Destination "$content/CrystalBenchBaseline/$file" -Force
    $baseline[$name]=(Get-FileHash -LiteralPath "$backup/$file").Hash
    if(Test-Path -LiteralPath "$content/$rel/$file"){
        # Prior attempts belong to this private host. Keep them with the new batch record.
        Move-Item -LiteralPath "$content/$rel/$file" -Destination "$run/prior-stage-$file"
    }
}
$exe='E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$env:UE_SKIP_UBT_SDK_SETUP='1'
$engineLog=Join-Path $run 'import.log'
$arguments=@(('"'+$stage+'/CrystalBench.uproject"'),'/Engine/Maps/Entry','-run=pythonscript',('-script="'+$PSScriptRoot+'/import_bench.py"'),'-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-AssetGatherAll=false','-NoAssetRegistryCacheWrite','-ExecCmds="Interchange.FeatureFlags.Import.FBX 0"',('-abslog="'+$engineLog+'"'))
$proc=Start-Process -FilePath $exe -ArgumentList $arguments -WindowStyle Hidden -PassThru
$null=$proc.Handle
$proc.WaitForExit()
$proc.Refresh()
if($proc.ExitCode -ne 0) { throw "Bench import failed ($($proc.ExitCode)). $engineLog" }
} else {
    if($InstallBatch -notmatch '^\d{8}-\d{6}-\d{3}$'){throw 'Invalid import batch'}
    foreach($name in $names){$baseline[$name]=(Get-FileHash -LiteralPath "$backup/$name.uasset").Hash}
}
$receipt=Get-Content -Raw -Encoding utf8 -LiteralPath "$PSScriptRoot/mesh-import.json" | ConvertFrom-Json
$mutex=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$committed=@()
try {
    try { $held=$mutex.WaitOne() } catch [Threading.AbandonedMutexException] {$held=$true}
    $openEditor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { !$_.CommandLine -or $_.CommandLine -like '*FPSGAME.uproject*' }
    if($openEditor){ throw 'Project editor open. Use the live asset bridge for these two packages.' }
    foreach($name in $names){
        $dst="$source/$rel/$name.uasset"
        if((Get-FileHash -LiteralPath $dst).Hash -ne $baseline[$name]){throw "Target changed during import: $dst"}
        if(!($receipt | Where-Object package -eq "/Game/$rel/$name")){throw "Missing import receipt for $name"}
        [IO.File]::Copy("$content/$rel/$name.uasset","$dst.crystal-tmp",$true)
    }
    foreach($name in $names){
        $dst="$source/$rel/$name.uasset"
        [IO.File]::Move("$dst.crystal-tmp",$dst,$true)
        $committed+=$name
    }
} catch {
    foreach($name in $committed){
        $dst="$source/$rel/$name.uasset"
        [IO.File]::Copy("$backup/$name.uasset","$dst.crystal-revert",$true)
        [IO.File]::Move("$dst.crystal-revert",$dst,$true)
    }
    throw
} finally {
    if($held){$mutex.ReleaseMutex()}
    $mutex.Dispose()
}
@{meshes=$receipt; backups=$backup; render=$false; gameplay_tested=$false} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath "$PSScriptRoot/installed.json" -Encoding utf8
Write-Output "Installed both bench meshes. $PSScriptRoot/installed.json"
