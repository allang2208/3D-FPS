$ErrorActionPreference='Stop'
$m24Root='D:/FPS3D/FPSGAME'
$m24Out="$m24Root/SourceAssets/M24ReloadGap20261029"
$m24Module="$m24Root/Intermediate/Build/Win64/x64/UnrealEditor/Development/FPSGAME"
$m24Toolchain='C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64'
$m24Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$m24Held=$false;$m24Pushed=$false
try {
    try{$m24Held=$m24Gate.WaitOne([TimeSpan]::FromMinutes(15))}catch [Threading.AbandonedMutexException]{$m24Held=$true}
    if(-not $m24Held){throw 'Existing UE batch is occupied.'}
    function Assert-M24BuildAvailable {
        $m24Busy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -in @('UnrealEditor.exe','UnrealEditor-Cmd.exe') -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or $_.Name -eq 'cl.exe'
        })
        if($m24Busy.Count){throw 'An editor or build currently owns the project. Nothing published.'}
    }
    Assert-M24BuildAvailable
    Push-Location -LiteralPath 'E:/Program Files (x86)/UE_5.8/Engine/Source';$m24Pushed=$true
    $m24Stage="$m24Out/Staging"
    [IO.Directory]::CreateDirectory($m24Stage) | Out-Null
    $m24Compile=[IO.File]::ReadAllText("$m24Module/FPSGAMECharacter.cpp.obj.rsp")
    $m24Compile=$m24Compile.Replace("$m24Module/FPSGAMECharacter.cpp.obj","$m24Stage/FPSGAMECharacter.cpp.obj").Replace("$m24Module/FPSGAMECharacter.cpp.sarif","$m24Stage/FPSGAMECharacter.cpp.sarif").Replace("$m24Module/FPSGAMECharacter.cpp.dep.json","$m24Stage/FPSGAMECharacter.cpp.dep.json")
    [IO.File]::WriteAllText("$m24Stage/compile.rsp",$m24Compile)
    & "$m24Toolchain/cl.exe" "@$m24Stage/compile.rsp" *> "$m24Out/compile-incremental.log"
    if($LASTEXITCODE -ne 0){throw 'M24 source compilation failed; existing DLL retained.'}
    $m24Link=[IO.File]::ReadAllText("$m24Module/UnrealEditor-FPSGAME.dll.rsp")
    $m24Link=$m24Link.Replace("$m24Module/FPSGAMECharacter.cpp.obj","$m24Stage/FPSGAMECharacter.cpp.obj").Replace("$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.dll","$m24Stage/UnrealEditor-FPSGAME.dll").Replace("$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.pdb","$m24Stage/UnrealEditor-FPSGAME.pdb")
    [IO.File]::WriteAllText("$m24Stage/link.rsp",$m24Link)
    & "$m24Toolchain/link.exe" "@$m24Stage/link.rsp" *> "$m24Out/link-incremental.log"
    if($LASTEXITCODE -ne 0){throw 'M24 linking failed; existing DLL retained.'}
    Assert-M24BuildAvailable
    Copy-Item -LiteralPath "$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.dll" -Destination "$m24Out/Backups/UnrealEditor-FPSGAME.dll"
    Copy-Item -LiteralPath "$m24Stage/UnrealEditor-FPSGAME.pdb" -Destination "$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.pdb" -Force
    Copy-Item -LiteralPath "$m24Stage/UnrealEditor-FPSGAME.dll" -Destination "$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.dll" -Force
    Copy-Item -LiteralPath "$m24Stage/FPSGAMECharacter.cpp.obj" -Destination "$m24Module/FPSGAMECharacter.cpp.obj" -Force
    Copy-Item -LiteralPath "$m24Stage/FPSGAMECharacter.cpp.dep.json" -Destination "$m24Module/FPSGAMECharacter.cpp.dep.json" -Force
    @{mode='incremental-native-rsp';exit_code=0;target='FPSGAMEEditor';completed=(Get-Date).ToString('o');runtime_tested=$false;ubt_blocker='Installed FabToolset missing from UE5Rules';compiled_source='FPSGAMECharacter.cpp';dll="$m24Root/Binaries/Win64/UnrealEditor-FPSGAME.dll"} | ConvertTo-Json | Set-Content -LiteralPath "$m24Out/build-receipt.json" -Encoding utf8
    Write-Output 'M24 native incremental compile and DLL link completed. No editor or game launched.'
} finally {if($m24Pushed){Pop-Location};if($m24Held){$m24Gate.ReleaseMutex()};$m24Gate.Dispose()}
