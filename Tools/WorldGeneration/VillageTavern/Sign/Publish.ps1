param([string]$EngineRoot='E:/Program Files (x86)/UE_5.8')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$stage=Join-Path $env:TEMP ('HillsVillageTavernSign-'+[Guid]::NewGuid().ToString('N'))
$config=Join-Path $stage 'Config'
New-Item -ItemType Directory -Path $config,(Join-Path $stage 'Content') -Force | Out-Null
$uproject=Join-Path $stage 'TavernSign.uproject'
@{
    FileVersion=3
    EngineAssociation='5.8'
    Plugins=@(@{Name='PythonScriptPlugin';Enabled=$true},@{Name='EditorScriptingUtilities';Enabled=$true})
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $uproject -Encoding UTF8
'[ConsoleVariables]', 'Interchange.FeatureFlags.Import.FBX=0' |
    Set-Content -LiteralPath (Join-Path $config 'DefaultEngine.ini') -Encoding UTF8
$exe=Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne()} catch [Threading.AbandonedMutexException] {$held=$true}
    $argsList=@(('"'+$uproject+'"'),'-run=pythonscript',('-script="'+$PSScriptRoot+'/import_sign.py"'),
        '-unattended','-nop4','-nosplash','-nosound','-NullRHI','-Multiprocess','-NoAssetRegistryCacheWrite',
        '-LocalDataCachePath=D:/FPS3D/DerivedDataCache',('-abslog="'+$stage+'/import.log"'))
    $oldSkip=$env:UE_SKIP_UBT_SDK_SETUP
    try {
        $env:UE_SKIP_UBT_SDK_SETUP='1'
        $proc=Start-Process -FilePath $exe -ArgumentList $argsList -WindowStyle Hidden -PassThru
        $null=$proc.Handle
        Write-Output "Saving tavern sign packages in $stage"
        $proc.WaitForExit()
        $proc.Refresh()
        if($proc.ExitCode -ne 0){throw "Sign commandlet exited with $($proc.ExitCode). $stage/import.log"}
    } finally {$env:UE_SKIP_UBT_SDK_SETUP=$oldSkip}
    $relativeDir='WorldGeneration/VillageTavern/Sign'
    $targetDir=Join-Path "$root/Content" $relativeDir
    $from=Join-Path "$stage/Content" $relativeDir
    $receipt=Get-Content -LiteralPath (Join-Path $stage 'saved.json') -Raw | ConvertFrom-Json
    New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    $outputs=foreach($package in $receipt){
        $name=[IO.Path]::GetFileName([string]$package)
        Get-Item -LiteralPath (Join-Path $from ($name+'.uasset'))
        Get-ChildItem -LiteralPath $from -File | Where-Object {$_.BaseName -eq $name -and $_.Extension -in @('.ubulk','.uexp','.uptnl')}
    }
    foreach($file in $outputs){
        if(Test-Path -LiteralPath (Join-Path $targetDir $file.Name)){throw "Destination exists: $($file.Name)"}
    }
    foreach($file in $outputs){
        [IO.File]::Copy($file.FullName,(Join-Path $targetDir $file.Name),$false)
        Write-Output "Published $($file.Name)"
    }
    Copy-Item -LiteralPath (Join-Path $stage 'saved.json') -Destination (Join-Path $root 'SourceAssets/HillsVillageTavern/Sign/saved.json') -Force
} finally {
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
