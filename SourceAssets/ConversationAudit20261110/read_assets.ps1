$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript ('-script='+$PSScriptRoot+'/read_assets.py') -nullrhi -nosound -unattended -nosplash ('-abslog='+$PSScriptRoot+'/assets.log') *> ($PSScriptRoot+'/assets.stdout.log')
    @{exit_code=$LASTEXITCODE;read_only=$true} | ConvertTo-Json | Set-Content ($PSScriptRoot+'/assets-receipt.json') -Encoding utf8
    Write-Output "ASSET_READBACK exit=$LASTEXITCODE"
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
