$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME/SourceAssets/Super90Duckbill20261016'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    try {$held=$gate.WaitOne(1800000)} catch [Threading.AbandonedMutexException] {$held=$true}
    if(-not $held){Write-Output 'ASSET_QUEUE_BUSY';exit 75}
    $editor=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") | Where-Object {$_.CommandLine -match '[\\/]FPSGAME[\\/]FPSGAME.uproject'}
    if($editor){
        $gate.ReleaseMutex();$held=$false
        & powershell -NoProfile -File 'D:/FPS3D/FPSGAME/Tools/AssetPipeline/mcp_call_codex.ps1' -PythonScript "$taskRoot/install_assets.py" -OutputFile "$taskRoot/install_bridge_01.json" -MaxOutputChars 1500 -QueueWaitSeconds 1800 -RequestTimeoutSeconds 300
    }else{
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript "-script=$taskRoot/install_assets.py" -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -d3d12 -RenderOffscreen "-abslog=$taskRoot/install_engine.log"
    }
    exit $LASTEXITCODE
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
