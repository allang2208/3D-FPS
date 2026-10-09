$ErrorActionPreference='Stop'
$projectRoot='D:/FPS3D/FPSGAME'
$taskRoot=Join-Path $projectRoot 'SourceAssets/Super90LoaderRepair20261008'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$previousSkipSdk=[Environment]::GetEnvironmentVariable('UE_SKIP_UBT_SDK_SETUP','Process')
try {
    for($attempt=0;$attempt -lt 30 -and -not $held;++$attempt) {
        try {$held=$gate.WaitOne(30000)} catch [Threading.AbandonedMutexException] {$held=$true}
        if($held){
            $busy=@(Get-CimInstance Win32_Process | Where-Object {
                ($_.Name -eq 'UnrealEditor-Cmd.exe' -and ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject')) -or
                $_.Name -eq 'cl.exe' -or $_.Name -eq 'link.exe' -or $_.Name -eq 'UnrealBuildTool.exe' -or
                ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
            })
            if($busy.Count){$gate.ReleaseMutex();$held=$false;Start-Sleep -Seconds 30}
        }
    }
    if(-not $held){throw 'Background asset/build batch remains busy. No processes stopped.'}
    # The project build helper also refuses loaded interactive editor modules.
    & "$projectRoot/Tools/Build/Build-Editor.ps1" *> "$taskRoot/build_console.log"
    if($LASTEXITCODE -ne 0){throw 'Native build failed; see build_console.log'}
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'" | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'
    })
    if($editors.Count){throw 'FPSGAME editor opened during the build; preserve it and resume import through its bridge.'}
    # The just-completed native build already resolved the local SDK. Avoid
    # a second Build.bat ValidatePlatforms query during this asset-only import.
    [Environment]::SetEnvironmentVariable('UE_SKIP_UBT_SDK_SETUP','1','Process')
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
        "$projectRoot/FPSGAME.uproject" -run=pythonscript "-script=$taskRoot/import_repair.py" `
        -unattended -nop4 -nosplash -nosound -nullrhi `
        "-abslog=$taskRoot/import_background.log" *> "$taskRoot/import_console.log"
    if($LASTEXITCODE -ne 0){throw 'Asset import failed; see import_background.log'}
    Write-Output 'SUPER90_R4_BUILD_AND_SAVE_FINISHED'
} finally {
    [Environment]::SetEnvironmentVariable('UE_SKIP_UBT_SDK_SETUP',$previousSkipSdk,'Process')
    if($held){$gate.ReleaseMutex()}
    $gate.Dispose()
}
