[CmdletBinding()]
param(
    [string]$EditorPath = 'E:\Program Files (x86)\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
)

# User-invoked launcher only. No tracing, tests, graphics settings, account-group
# changes or persistent compatibility flags are applied by this script.
$ErrorActionPreference = 'Stop'
try {
    $captureProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
    $captureProjectFile = Join-Path $captureProjectRoot 'FPSGAME.uproject'
    if (-not (Test-Path -LiteralPath $captureProjectFile -PathType Leaf)) {
        throw "Project not found: $captureProjectFile"
    }
    if (-not (Test-Path -LiteralPath $EditorPath -PathType Leaf)) {
        throw "UE editor not found: $EditorPath"
    }
    $captureEditors = @(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe' OR Name='UnrealEditor-Cmd.exe'")
    $captureProjectEditors = @($captureEditors | Where-Object {
        [string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match [regex]::Escape('FPSGAME.uproject')
    })
    if ($captureProjectEditors.Count -gt 0) {
        $capturePids = ($captureProjectEditors.ProcessId -join ', ')
        throw "Save your work and exit the existing FPSGAME editor/commandlet first (PID: $capturePids). No process was closed."
    }
    $captureArguments = '"{0}"' -f $captureProjectFile
    # The user's Windows UAC confirmation grants this new UE process its token.
    # Opening a project through the Epic launcher does not provide that guarantee.
    Start-Process -FilePath $EditorPath -ArgumentList $captureArguments -WorkingDirectory $captureProjectRoot -Verb RunAs | Out-Null
    Write-Host 'UE launch requested with administrator rights. Start the recording yourself in F6.'
    Write-Host 'Wait for the F6 status to show WDDM + UE recording before reproducing the stall.'
    exit 0
}
catch {
    $captureFailure = $_.Exception.GetBaseException()
    if ($captureFailure -is [ComponentModel.Win32Exception] -and $captureFailure.NativeErrorCode -eq 1223) {
        Write-Host 'Windows permission prompt was cancelled. No capture was started.' -ForegroundColor Yellow
    }
    else {
        Write-Host $captureFailure.Message -ForegroundColor Red
    }
    exit 1
}
