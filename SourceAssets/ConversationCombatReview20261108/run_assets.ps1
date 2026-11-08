$ErrorActionPreference='Stop'
$project='D:/FPS3D/FPSGAME';$out=$PSScriptRoot
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied; no asset readback started.'}
    if(Get-Process UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$project/FPSGAME.uproject" -run=pythonscript "-script=$out/read_assets.py" -unattended -nop4 -nosplash -nosound -nullrhi -Multiprocess '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$out/assets.log" *> "$out/assets.console.log"
    $code=$LASTEXITCODE
    @{exit_code=$code;read_only=$true;rendered=$false} | ConvertTo-Json | Set-Content -LiteralPath "$out/assets-receipt.json" -Encoding utf8
    Write-Output "ASSETS_DONE exit=$code"
    exit $code
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
