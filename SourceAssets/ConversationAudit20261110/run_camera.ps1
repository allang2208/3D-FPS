$ErrorActionPreference='Stop'
$root='D:/FPS3D/FPSGAME';$run=Join-Path $PSScriptRoot ('Camera/'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false;$failed=$false
try {
    try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(20))}catch [Threading.AbandonedMutexException]{$held=$true}
    if(-not $held){throw 'UE batch occupied.'}
    if(Get-Process UnrealEditor,UnrealEditor-Cmd,FPSGAME -ErrorAction SilentlyContinue){throw 'Existing UE process preserved.'}
    foreach($body in @('jason','kaitlin')){
        $out=Join-Path $run $body;New-Item -ItemType Directory -Force -Path $out | Out-Null
        & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' ($root+'/FPSGAME.uproject') -run=LeapStrikeAudit -CameraOnly ('-CameraBody='+$body) ('-Out='+$out) -nullrhi -nosound -unattended -nop4 ('-abslog='+$out+'/engine.log') *> ($out+'/stdout.log')
        $code=$LASTEXITCODE;$failed=$failed -or $code -ne 0
        @{body=$body;exit_code=$code;dll_sha256=(Get-FileHash ($root+'/Binaries/Win64/UnrealEditor-FPSGAME.dll')).Hash;rendered=$false} | ConvertTo-Json | Set-Content ($out+'/receipt.json') -Encoding utf8
        Write-Output "CAMERA_RESULT body=$body exit=$code path=$out"
    }
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
if($failed){exit 1}
