$ErrorActionPreference='Stop'
$bowShellGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$bowShellHeld=$false
try{
    Write-Output 'Waiting for the shared UE review batch.'
    try{$bowShellHeld=$bowShellGate.WaitOne([TimeSpan]::FromMinutes(30))}catch [Threading.AbandonedMutexException]{$bowShellHeld=$true}
    if(-not $bowShellHeld){throw 'UE review batch remained busy.'}
    Write-Output 'BOW_REVIEW_BATCH_READY'
    while($null -ne ($bowCommand=[Console]::ReadLine())){
        if($bowCommand -eq 'exit'){break}
        if([string]::IsNullOrWhiteSpace($bowCommand)){continue}
        try{& ([scriptblock]::Create($bowCommand))}catch{Write-Output $_}
        Write-Output "BOW_REVIEW_COMMAND_COMPLETE exit=$LASTEXITCODE"
    }
}finally{if($bowShellHeld){$bowShellGate.ReleaseMutex()};$bowShellGate.Dispose()}
