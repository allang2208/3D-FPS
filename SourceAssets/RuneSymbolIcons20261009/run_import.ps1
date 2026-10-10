$ErrorActionPreference='Stop'
$gate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    Write-Output 'Waiting for the existing UE asset batch to release the bridge gate.'
    while (-not $held) {
        try { $held=$gate.WaitOne([TimeSpan]::FromSeconds(30)) }
        catch [Threading.AbandonedMutexException] { $held=$true }
    }
    if(Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue) {
        throw 'An interactive editor appeared; use its bridge instead.'
    }
    Write-Output 'UE asset gate acquired; saving rune icon textures in background.'
    $project=Join-Path $PSScriptRoot '../../FPSGAME.uproject'
    $project=[IO.Path]::GetFullPath($project)
    $scriptFile=Join-Path $PSScriptRoot 'import_icons.py'
    $log=Join-Path $PSScriptRoot 'import-headless-02.log'
    $stdout=Join-Path $PSScriptRoot 'import-headless-02-stdout.log'
    & 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' $project '-run=pythonscript' "-script=$scriptFile" '-nullrhi' '-unattended' '-nosplash' '-nosound' '-multiprocess' '-stdout' "-abslog=$log" *> $stdout
    $importCode=$LASTEXITCODE
    Write-Output "Rune icon import exit: $importCode"
    Get-Content -LiteralPath $stdout -Tail 22
    if($importCode -ne 0) { throw "Import commandlet failed: $importCode" }
} finally {
    if($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
