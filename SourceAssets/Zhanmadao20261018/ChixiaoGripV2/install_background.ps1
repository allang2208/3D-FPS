$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
 try {$held=$gate.WaitOne([TimeSpan]::FromMinutes(30))} catch [Threading.AbandonedMutexException] {$held=$true}
 if(-not $held){throw 'Animation save queue timed out'}
 if(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue){throw 'An editor is active; preserve it and use the existing editor bridge'}
 & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript ("-script="+(Join-Path $PSScriptRoot 'install_grip.py')) -unattended -nosplash -NullRHI -NoSound -NoP4 -UTF8Output ("-abslog="+(Join-Path $PSScriptRoot 'install-commandlet.log')) *> (Join-Path $PSScriptRoot 'install-console.log')
 $result=$LASTEXITCODE
 @{exit_code=$result;finished=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot 'commandlet-receipt.json') -Encoding UTF8
 if($result -ne 0){throw "Animation save failed ($result)"}
 Write-Output 'CHIXIAO_GRIP_ASSETS_SAVED'
} finally {if($held){$gate.ReleaseMutex()};$gate.Dispose()}