param([switch]$StageOnly,[switch]$PublishOnly,
    [string[]]$CompileUnits=@('FPSGAMECharacter.cpp','M24OpticVisual.cpp','M4GunsmithVisual.cpp','ScopeOpticalPresentation.cpp','ColdSteelCrosshair.cpp'),
    [string]$OutputDirectory='D:/FPS3D/FPSGAME/SourceAssets/M24DualOptic20261029')
$ErrorActionPreference='Stop'
$m24Root='D:/FPS3D/FPSGAME'
$m24Out=$OutputDirectory
$m24Module="$m24Root/Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME"
$m24Toolchain='C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64'
$m24Units=$CompileUnits
$m24Stage="$m24Out/Staging"
$m24Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$m24Held=$false;$m24Pushed=$false
function Assert-M24BuildAvailable([bool]$RequireClosed) {
    $m24Busy=@(Get-CimInstance Win32_Process | Where-Object {
        ($RequireClosed -and $_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -in @('cl.exe','link.exe')
    })
    if($m24Busy.Count){throw 'An editor or build owns the requested publication target. Existing DLL retained.'}
}
try {
    try{$m24Held=$m24Gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$m24Held=$true}
    if(-not $m24Held){throw 'Existing UE batch is occupied.'}
    Assert-M24BuildAvailable (-not $StageOnly)
    Push-Location -LiteralPath 'E:/Program Files (x86)/UE_5.8/Engine/Source';$m24Pushed=$true
    [IO.Directory]::CreateDirectory($m24Stage) | Out-Null
    if(-not $PublishOnly){
        foreach($m24Unit in $m24Units){
            $m24Compile=[IO.File]::ReadAllText("$m24Module/$m24Unit.obj.rsp")
            foreach($m24Suffix in @('obj','sarif','dep.json')){
                $m24Compile=$m24Compile.Replace("$m24Module/$m24Unit.$m24Suffix","$m24Stage/$m24Unit.$m24Suffix")
            }
            [IO.File]::WriteAllText("$m24Stage/$m24Unit.rsp",$m24Compile)
            & "$m24Toolchain/cl.exe" "@$m24Stage/$m24Unit.rsp" *> "$m24Out/compile-$m24Unit.log"
            if($LASTEXITCODE -ne 0){throw "M24 compilation failed: $m24Unit. Existing DLL retained."}
            Write-Output "Compiled $m24Unit"
        }
    }
    # Relink against the current module objects, preserving other completed work.
    $m24Link=[IO.File]::ReadAllText("$m24Module/UnrealEditor-FPSGAME.dll.rsp")
    foreach($m24Unit in $m24Units){$m24Link=$m24Link.Replace("$m24Module/$m24Unit.obj","$m24Stage/$m24Unit.obj")}
    $m24Link=$m24Link.Replace("$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.dll","$m24Stage/UnrealEditor-FPSGAME.dll").Replace("$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.pdb","$m24Stage/UnrealEditor-FPSGAME.pdb")
    [IO.File]::WriteAllText("$m24Stage/link.rsp",$m24Link)
    & "$m24Toolchain/link.exe" "@$m24Stage/link.rsp" *> "$m24Out/link-incremental.log"
    if($LASTEXITCODE -ne 0){throw 'M24 linking failed; existing DLL retained.'}
    if(-not $StageOnly){
        Assert-M24BuildAvailable $true
        [IO.Directory]::CreateDirectory("$m24Out/Backups") | Out-Null
        $m24Stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
        Copy-Item -LiteralPath "$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.dll" -Destination "$m24Out/Backups/UnrealEditor-FPSGAME-$m24Stamp.dll"
        Copy-Item -LiteralPath "$m24Stage/UnrealEditor-FPSGAME.pdb" -Destination "$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.pdb" -Force
        Copy-Item -LiteralPath "$m24Stage/UnrealEditor-FPSGAME.dll" -Destination "$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.dll" -Force
        foreach($m24Unit in $m24Units){
            foreach($m24Suffix in @('obj','dep.json')){
                Copy-Item -LiteralPath "$m24Stage/$m24Unit.$m24Suffix" -Destination "$m24Module/$m24Unit.$m24Suffix" -Force
            }
        }
    }
    @{mode='incremental-native-rsp';exit_code=0;target='FPSGAMEEditor';completed=(Get-Date).ToString('o');runtime_tested=$false;compiled_sources=$m24Units;published=(-not $StageOnly);dll="$m24Stage/UnrealEditor-FPSGAME.dll"} | ConvertTo-Json | Set-Content -LiteralPath "$m24Out/build-receipt.json" -Encoding utf8
    Write-Output "M24 dual optic compiled and linked. Published=$(-not $StageOnly). No editor or game launched."
} finally {if($m24Pushed){Pop-Location};if($m24Held){$m24Gate.ReleaseMutex()};$m24Gate.Dispose()}
