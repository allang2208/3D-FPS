# Give the caller's writable packages private copies; link their read-only dependencies.
function New-YardAuthorHost($project,$run,$contentRoot,$private=@(
    'WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap',
    'WorldGeneration/TemperateHills/VillageCarpenter/YardDetail',
    'WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterPlaneFiber.uasset')) {
    $authorDir=Join-Path $run 'Host'
    New-Item -ItemType Directory -Force -Path "$authorDir/Content","$authorDir/Binaries/Win64" | Out-Null
    Copy-Item -LiteralPath "$project/FPSGAME.uproject","$project/Config" -Destination $authorDir -Recurse
    $moduleList="$project/Binaries/Win64/UnrealEditor.modules"
    Copy-Item -LiteralPath $moduleList -Destination "$authorDir/Binaries/Win64"
    foreach($mod in (Get-Content -Raw $moduleList | ConvertFrom-Json).Modules.PSObject.Properties) {
        Copy-Item -LiteralPath (Join-Path "$project/Binaries/Win64" $mod.Value) -Destination "$authorDir/Binaries/Win64"
    }
    foreach ($name in 'Plugins','Shaders') {
        New-Item -ItemType Junction -Path "$authorDir/$name" -Target "$project/$name" | Out-Null
    }
    function Add-ContentBranch([string]$branch) {
        $sourceDir=Join-Path $contentRoot $branch
        $destDir=Join-Path "$authorDir/Content" $branch
        [IO.Directory]::CreateDirectory($destDir) | Out-Null
        foreach($item in Get-ChildItem -LiteralPath $sourceDir -Force) {
            $piece=($branch+'/'+$item.Name).TrimStart('/')
            if($piece -in $private) {
                Copy-Item -LiteralPath $item.FullName -Destination $destDir -Recurse
            } elseif($item.PSIsContainer) {
                if(@($private | Where-Object { $_.StartsWith($piece+'/',[StringComparison]::OrdinalIgnoreCase) }).Count) {
                    Add-ContentBranch $piece
                } else {
                    New-Item -ItemType Junction -Path (Join-Path $destDir $item.Name) -Target $item.FullName | Out-Null
                }
            } else {
                New-Item -ItemType HardLink -Path (Join-Path $destDir $item.Name) -Target $item.FullName | Out-Null
            }
        }
    }
    Add-ContentBranch ''
    return "$authorDir/FPSGAME.uproject"
}
