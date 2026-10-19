$ErrorActionPreference='Stop'
$s12Root='D:/FPS3D/FPSGAME'
$s12Out="$s12Root/SourceAssets/Saiga12KResonance20261019/Receipts"
$s12Gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$s12Held=$false
try {
    try { $s12Held=$s12Gate.WaitOne([TimeSpan]::FromMinutes(10)) }
    catch [Threading.AbandonedMutexException] { $s12Held=$true; throw 'Abandoned UE batch; preserve state.' }
    if(-not $s12Held) { throw 'UE batch timeout; no commandlet started.' }
    if(Get-Process UnrealEditor -ErrorAction SilentlyContinue) { throw 'Interactive editor exists; use the existing editor bridge.' }
    $env:UE_SKIP_UBT_SDK_SETUP='1'
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$s12Root/FPSGAME.uproject" -run=pythonscript "-script=$s12Root/Tools/Saiga12KResonance/install_fit.py" -NullRHI -unattended -nop4 -nosound -nosplash '-ExecCmds=Editor.AsyncSkinnedAssetCompilation 0' '-LocalDataCachePath=D:/FPS3D/DerivedDataCache' "-abslog=$s12Out/save-headless.log" *> "$s12Out/save-headless-console.log"
    $s12Exit=$LASTEXITCODE
    @{exit_code=$s12Exit;completed=(Get-Date).ToString('o');interactive_editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$s12Out/save-headless-process.json" -Encoding utf8
    if($s12Exit -ne 0) { throw "S12K asset save failed: $s12Exit" }
} finally {
    if($s12Held) { $s12Gate.ReleaseMutex() }
    $s12Gate.Dispose()
}
