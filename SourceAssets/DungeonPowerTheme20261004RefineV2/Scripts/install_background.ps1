<#
Future explicit local installation only. This delivered script has NOT been run.
It refuses a live FPSGAME editor and never kills processes or edits defaults.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProjectRoot,
    [Parameter(Mandatory=$true)][string]$UnrealEditorCmd,
    [switch]$AuthorizeProjectWrites,
    [ValidateSet('All','Assets','Subject')][string]$Stage='All',
    [ValidateRange(1,120)][int]$MutexWaitMinutes=15
)
$ErrorActionPreference='Stop'
if (-not $AuthorizeProjectWrites) {
    throw 'No changes made. Local project writes require explicit user authorization and -AuthorizeProjectWrites.'
}
$taskRoot=(Resolve-Path (Split-Path $PSScriptRoot -Parent)).Path
$project=(Resolve-Path $ProjectRoot).Path.TrimEnd('\','/')
$expected=Join-Path $project 'SourceAssets\DungeonPowerTheme20261004RefineV2'
if (-not [string]::Equals($taskRoot.TrimEnd('\','/'),$expected.TrimEnd('\','/'),[StringComparison]::OrdinalIgnoreCase)) {
    throw 'Stage the approved package under the selected project SourceAssets first. This wrapper never copies into a project.'
}
$uproject=Join-Path $project 'FPSGAME.uproject'
if (-not (Test-Path -LiteralPath $uproject -PathType Leaf)) {throw 'FPSGAME.uproject is absent.'}
$exe=(Resolve-Path -LiteralPath $UnrealEditorCmd).Path
if ([IO.Path]::GetFileName($exe) -ne 'UnrealEditor-Cmd.exe') {throw 'An explicit Windows UnrealEditor-Cmd.exe path is required.'}
$versionPath=Join-Path (Split-Path (Split-Path (Split-Path $exe -Parent) -Parent) -Parent) 'Build\Build.version'
if (-not (Test-Path -LiteralPath $versionPath -PathType Leaf)) {throw 'Cannot read the selected engine Build.version.'}
$version=Get-Content -LiteralPath $versionPath -Raw | ConvertFrom-Json
if ($version.MajorVersion -ne 5 -or $version.MinorVersion -ne 8 -or $version.PatchVersion -ne 3) {
    throw 'This delivery targets the inventoried UE 5.8.3. Choose its exact commandlet executable.'
}
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$held=$false
try {
    $deadline=[DateTime]::UtcNow.AddMinutes($MutexWaitMinutes)
    while (-not $held -and [DateTime]::UtcNow -lt $deadline) {
        try {$held=$taskGate.WaitOne(5000)} catch [Threading.AbandonedMutexException] {$held=$true}
    }
    if (-not $held) {throw 'Shared UE batch mutex is busy; no process was launched.'}
    $active=Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and $_.CommandLine -match 'FPSGAME'
    }
    if ($active) {throw 'Preserve existing FPSGAME editor/commandlet processes. No process was launched or killed.'}
    $receipts=Join-Path $taskRoot 'Receipts'
    New-Item -ItemType Directory -Force -Path $receipts | Out-Null
    $scripts=@()
    if ($Stage -eq 'All' -or $Stage -eq 'Assets') {$scripts+='import_assets.py'}
    if ($Stage -eq 'All' -or $Stage -eq 'Subject') {$scripts+='build_subject_map.py'}
    foreach ($script in $scripts) {
        $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
        $log=Join-Path $receipts ($script.Replace('.py','')+'-'+$stamp+'.log')
        & $exe $uproject '-run=pythonscript' ('-script='+(Join-Path $PSScriptRoot $script)) `
            '-PowerThemeAuthorizeWrite' '-unattended' '-nop4' '-nosplash' '-nosound' '-nullrhi' ('-abslog='+$log) *> ($log+'.stdout')
        if ($LASTEXITCODE -ne 0) {throw "$script failed (exit $LASTEXITCODE). Preserve its log; no automatic overwrite or retry."}
    }
    Write-Output 'Requested commandlet stages returned success. Consult actual stage receipts; no game, render or test was run.'
} finally {
    if ($held) {$taskGate.ReleaseMutex()}
    $taskGate.Dispose()
}
