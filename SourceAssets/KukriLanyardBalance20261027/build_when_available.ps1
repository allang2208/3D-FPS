$ErrorActionPreference='Stop'
$deadline=(Get-Date).AddMinutes(20)
$project='D:\FPS3D\FPSGAME\FPSGAME.uproject'
while ((Get-Date) -lt $deadline) {
    $busy=@(Get-CimInstance Win32_Process | Where-Object {
        ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
        $_.Name -eq 'cl.exe' -or
        ($_.Name -match '^UnrealEditor.*\.exe$' -and $_.CommandLine -and $_.CommandLine.Replace('/','\').Contains($project))
    })
    if ($busy.Count -gt 0) {
        Write-Output ('Waiting for build/module users: '+(($busy | ForEach-Object {$_.ProcessId}) -join ','))
        Wait-Process -Id $busy.ProcessId -Timeout 50 -ErrorAction SilentlyContinue
        continue
    }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Build\BatchFiles\Build.bat' FPSGAMEEditor Win64 Development "-Project=$project" -NoHotReloadFromIDE *> (Join-Path $PSScriptRoot 'build-editor.log')
    exit $LASTEXITCODE
}
throw 'The project module remains in use; the source and catalog are saved, but the new DLL has not been built.'
