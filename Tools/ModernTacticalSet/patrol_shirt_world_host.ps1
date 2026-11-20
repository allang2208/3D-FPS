param([switch]$BuildOnly,[switch]$TacticalOnly,[ValidateSet('Jason','Kaitlin')][string]$RebuildBody,[switch]$RestoreRigDependencies)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$world=Join-Path $root 'SourceAssets/ModernTacticalSet20261113/PatrolShirtR2/World'
$hostRoot=Join-Path $world 'NativeHost'
$original=Join-Path $PSScriptRoot 'ShoulderFitHost'
$module=Join-Path $hostRoot 'Source/ShoulderFit'
$content=Join-Path $hostRoot 'Content'
New-Item -ItemType Directory -Force -Path $module,$content | Out-Null
foreach($name in @('AsianMale_Jason','Characters','Items','Weapons')){
    $path=Join-Path $content $name
    $target=(Resolve-Path (Join-Path $root ('Content/'+$name))).Path
    if(!(Test-Path -LiteralPath $path)){ New-Item -ItemType Junction -Path $path -Target $target | Out-Null }
    if((Get-Item -LiteralPath $path).Target -ne $target){throw "Unexpected content mount $path"}
}
function Set-Source($source,$dest){
    if(!(Test-Path -LiteralPath $dest) -or (Get-FileHash -LiteralPath $dest).Hash -ne (Get-FileHash -LiteralPath $source).Hash){
        Copy-Item -LiteralPath $source -Destination $dest
    }
}
foreach($rel in @('.gitignore','Source/ShoulderFitEditor.Target.cs','Source/ShoulderFit/RefitShoulderCommandlet.h')){
    Set-Source (Join-Path $original $rel) (Join-Path $hostRoot $rel)
}
Set-Source (Join-Path $PSScriptRoot 'patrol_shirt_world_native.cpp') (Join-Path $module 'RefitShoulderCommandlet.cpp')
$buildRules=(Get-Content (Join-Path $original 'Source/ShoulderFit/ShoulderFit.Build.cs') -Raw).Replace('"StaticMeshDescription"','"StaticMeshDescription","SkeletalMeshDescription","AnimationCore","TargetPlatform","SkeletalMeshUtilitiesCommon"')
$buildCs=Join-Path $module 'ShoulderFit.Build.cs'
if(!(Test-Path -LiteralPath $buildCs) -or [IO.File]::ReadAllText($buildCs) -ne $buildRules){[IO.File]::WriteAllText($buildCs,$buildRules)}
$engine='E:/Program Files (x86)/UE_5.8/Engine'
$project=Join-Path $hostRoot 'ShoulderFit.uproject'
$projectData=Get-Content -Raw -LiteralPath (Join-Path $original 'ShoulderFit.uproject') | ConvertFrom-Json
$projectData.Plugins+=@([pscustomobject]@{Name='FullBodyIK';Enabled=$true})
$projectText=$projectData | ConvertTo-Json -Depth 8
if(!(Test-Path -LiteralPath $project) -or [IO.File]::ReadAllText($project) -ne $projectText){[IO.File]::WriteAllText($project,$projectText)}
& (Join-Path $engine 'Build/BatchFiles/Build.bat') 'ShoulderFitEditor' 'Win64' 'Development' "-Project=$project" '-WaitMutex' '-NoHotReload' '-NoHotReloadFromIDE' '-MaxParallelActions=3'
if($LASTEXITCODE){ throw 'Native shirt tailor build failed' }
if($BuildOnly){return}
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
try{
    $batches=Get-ChildItem -LiteralPath (Join-Path $world 'Fits') -Filter 'batch-*-00.txt' | Sort-Object Name
    $tacticalKeys=@()
    if($TacticalOnly){
        $routes=Get-Content -LiteralPath (Join-Path $world 'routes.json') -Raw | ConvertFrom-Json
        $tacticalKeys=@($routes.psobject.Properties | Where-Object {$_.Value.tactical} | ForEach-Object Name)
    }
    foreach($b in $batches){
        if($RebuildBody -and $b.Name -ne "batch-$RebuildBody-00.txt"){continue}
        $active=@(Get-Content -LiteralPath $b.FullName | Where-Object {
            $f=$_ -split '\|'
            $package=Join-Path $root ('Content/'+$f[1].Substring(6)+'.uasset')
            if($TacticalOnly){$tacticalKeys -contains $f[2]}else{ $RebuildBody -or !(Test-Path -LiteralPath (Join-Path $world ('Fits/'+$f[2]+'.saved'))) -or !(Test-Path -LiteralPath $package) }
        })
        if($active.Count -eq 0){continue}
        $list=Join-Path $world ('Fits/'+$b.BaseName+'.active')
        [IO.File]::WriteAllLines($list,[string[]]$active)
        $log=Join-Path $world ($b.BaseName+'-'+(Get-Date -Format 'HHmmss')+'.log')
        $held=$false
        $extra=@()
        if($RestoreRigDependencies){$extra+='-RestoreRigDependencies'}
        try{
            try{$held=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{$held=$true}
            & (Join-Path $engine 'Binaries/Win64/UnrealEditor-Cmd.exe') $project '/Engine/Maps/Entry' '-run=RefitShoulder' "-Work=$world" "-List=$list" @extra '-unattended' '-nosound' '-nop4' '-nosplash' '-NullRHI' '-Multiprocess' '-AssetGatherAll=false' '-asyncskinnedassetcompilation=0' "-abslog=$log" *> "$log.stdout"
            if($LASTEXITCODE){throw "Waist commandlet exited $LASTEXITCODE at $log"}
        }finally{if($held){$gate.ReleaseMutex()}}
    }
}finally{$gate.Dispose()}
