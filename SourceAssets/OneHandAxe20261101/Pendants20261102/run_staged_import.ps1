param([string]$ScriptName = 'import_icons.py')
$ErrorActionPreference = 'Stop'
# Use the same batch mutex as the project bridge. This isolated project never
# loads or saves FPSGAME packages, so an unavailable live editor is preserved.
$gate = [Threading.Mutex]::new($false, 'Local\CodexUeMcp-Port-8000')
$held = $false
try {
    try { $held = $gate.WaitOne([TimeSpan]::FromSeconds(60)) }
    catch [Threading.AbandonedMutexException] {
        $held = $true
        throw 'Prior UE bridge operation has unknown completion state; this import was not launched.'
    }
    if (-not $held) { throw 'UE batch gate is busy; this import was not launched.' }
    $env:UE_SKIP_UBT_SDK_SETUP = '1'
    $projectPath = Join-Path $PSScriptRoot 'ImportProject/PendantIconImport.uproject'
    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    $logName = [IO.Path]::GetFileNameWithoutExtension($ScriptName)
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' $projectPath -run=pythonscript "-script=$scriptPath" -unattended -nop4 -nosplash -NullRHI -nosound "-abslog=$PSScriptRoot/$logName-staged.log" *> "$PSScriptRoot/$logName-staged-console.log"
    $code = $LASTEXITCODE
} finally {
    if ($held) { $gate.ReleaseMutex() }
    $gate.Dispose()
}
exit $code
