$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try{try{$held=$gate.WaitOne([TimeSpan]::FromMinutes(10))}catch [Threading.AbandonedMutexException]{$held=$true}
if(!$held){throw 'UE batch busy'}
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript '-script=D:/FPS3D/FPSGAME/SourceAssets/SniperSuppressor20261019/ScaleRepair20261019/reimport.py' -nullrhi -nosound -unattended -nop4 -nosplash '-abslog=D:/FPS3D/FPSGAME/SourceAssets/SVCHNetworkReview20261019/scale-import.log' *> 'D:/FPS3D/FPSGAME/SourceAssets/SVCHNetworkReview20261019/scale-import-console.log'
}finally{if($held){$gate.ReleaseMutex()};$gate.Dispose()}
