param([Parameter(Mandatory=$true)][string]$Batch,[ValidateSet("R2","R3","R4","WorkwearR5","WorkwearR6")][string]$Revision)
$ErrorActionPreference='Stop'
$project=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$runner=Join-Path $Batch 'install.py'
$script=Join-Path $PSScriptRoot 'install_head.py'
$entry="from runpy import run_path`nfrom pathlib import Path`nrun_path(r'$script')['install'](Path(r'$Batch'),'$Revision')"
[IO.File]::WriteAllText($runner,$entry,[Text.UTF8Encoding]::new($false))
$receipt=Join-Path $Batch 'published.json'
while(!(Test-Path -LiteralPath $receipt)){
    if(Test-Path -LiteralPath (Join-Path $Batch 'superseded.txt')){return}
    $editor=Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match '(?i)[\\/]FPSGAME\.uproject(?:["\s]|$)' }
    if($editor) {
        & "$project/Tools/AssetPipeline/mcp_call_codex.ps1" -PythonScript $runner
        $code=$LASTEXITCODE
        if($code -ne 0){
            if (!(Get-Process -Id $editor.ProcessId -ErrorAction SilentlyContinue)){continue}
            throw 'Existing editor could not install the head.'
        }
    } else {
        $gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
        try{
            try{$null=$gate.WaitOne()}catch [Threading.AbandonedMutexException]{}
            if(!(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object { $_.CommandLine -match '(?i)[\\/]FPSGAME\.uproject(?:["\s]|$)' })){
                & py -3.11 $runner
                if($LASTEXITCODE -ne 0){throw 'Offline head installation failed.'}
            }
        } finally {$gate.ReleaseMutex();$gate.Dispose()}
    }
    if(!(Test-Path -LiteralPath $receipt)){Start-Sleep -Seconds 24}
}
