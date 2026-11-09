$ErrorActionPreference='Stop'
$batch=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000');$held=$false
try {
try {$held=$batch.WaitOne([TimeSpan]::FromMinutes(20))} catch [Threading.AbandonedMutexException] {$held=$true}
if(!$held){throw 'Final review batch wait expired'}
& "$PSScriptRoot/run.ps1" -Script readback.py
$samples=(0..54 | ForEach-Object {($_/60.0).ToString('0.000000',[Globalization.CultureInfo]::InvariantCulture)}) -join ','
& "$PSScriptRoot/review.ps1" -Label accepted -View left -Times $samples
& "$PSScriptRoot/review.ps1" -Label accepted -View left -Retract -Times '0,0.075,0.15,0.225,0.3,0.3375,0.45,0.5625,0.675,0.825,0.9'
& "$PSScriptRoot/review.ps1" -Label accepted -View player -Times '0,0.1125,0.225,0.39375,0.5625,0.6,0.646875,0.703125,0.7875,0.825,0.9'
}finally{if($held){$batch.ReleaseMutex()};$batch.Dispose()}
