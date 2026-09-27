param([int]$QueueSeconds=60)
$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME/Tools/Weapons/ScopeOptics20260927'
$taskOut='D:/FPS3D/FPSGAME/Saved/ScopeOptics20260927'
[IO.Directory]::CreateDirectory($taskOut) | Out-Null
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
$bridge=$false
try {
    try {$held=$gate.WaitOne([TimeSpan]::FromSeconds($QueueSeconds))}
    catch [Threading.AbandonedMutexException] {$held=$true;throw 'Previous UE batch completion is unknown; no asset operation sent.'}
    if(-not $held){throw 'UE batch gate occupied; no material operation started.'}
    $running=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe' OR Name='dotnet.exe' OR Name='cl.exe' OR Name='link.exe'" | Where-Object {
        $_.Name -in @('cl.exe','link.exe') -or -not $_.CommandLine -or $_.CommandLine -match 'FPSGAME|UnrealBuildTool'
    })
    if($running | Where-Object {$_.Name -ne 'UnrealEditor.exe'}){throw 'Build or commandlet active; no material operation started.'}
    if($running.Count){$bridge=$true}
    else {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$taskRoot/create_optical_material.py" -unattended -nop4 -nosplash -nosound -RenderOffscreen "-abslog=$taskOut/material-commandlet.log" *> "$taskOut/material-commandlet-stdout.txt"
        $result=$LASTEXITCODE
        Select-String -LiteralPath "$taskOut/material-commandlet.log" -Pattern 'SCOPE_OPTICS|LogPython: Error|Failed to compile Material|LogShaderCompilers: Error' | Select-Object -Last 15 | ForEach-Object {$_.Line}
        if($result -ne 0){throw "Material authoring failed: $result"}
    }
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}
if($bridge){
    $stamp=Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    & 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript "$taskRoot/create_optical_material.py" -QueueWaitSeconds $QueueSeconds -OutputFile "$taskOut/material-$stamp.bridge.txt" -MaxOutputChars 2200
    if($LASTEXITCODE -ne 0){throw 'Existing-editor material save did not complete.'}
}
