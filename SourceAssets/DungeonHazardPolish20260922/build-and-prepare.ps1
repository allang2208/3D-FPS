$ErrorActionPreference='Stop'
$taskRoot='D:\FPS3D\FPSGAME\SourceAssets\DungeonHazardPolish20260922'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $held=$gate.WaitOne([TimeSpan]::FromSeconds(300))
    if (-not $held) { throw 'UE integration queue timed out; no operation submitted.' }
    & 'D:\FPS3D\FPSGAME\Tools\Build\Build-Editor.ps1'
    if ($LASTEXITCODE -ne 0) { throw 'Native build failed.' }
    $editors=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    if ($editors | Where-Object { $_.CommandLine -match 'FPSGAME.uproject' }) { throw 'Project editor opened during build; preserve it and import through the live bridge.' }
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'D:\FPS3D\FPSGAME\FPSGAME.uproject' '-run=pythonscript' '-script=D:/FPS3D/FPSGAME/SourceAssets/DungeonHazardPolish20260922/Scripts/prepare_assets.py' '-Unattended' '-NullRHI' '-NoSound' '-NoSplash' '-UTF8Output' '-abslog=D:/FPS3D/FPSGAME/SourceAssets/DungeonHazardPolish20260922/prepare-offline.log'
    if ($LASTEXITCODE -ne 0) { throw 'Asset preparation failed; retain partial receipts.' }
} finally { if ($held) { $gate.ReleaseMutex() };$gate.Dispose() }
