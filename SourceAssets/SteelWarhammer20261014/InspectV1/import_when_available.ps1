$ErrorActionPreference='Stop'
while($inspectBuilds=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
    foreach($inspectBuild in $inspectBuilds) {
        Write-Output ('Waiting for active UBT process '+$inspectBuild.ProcessId)
        try { Wait-Process -Id $inspectBuild.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
    }
}
while($inspectCommandlets=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' })) {
    foreach($inspectCommandlet in $inspectCommandlets) {
        Write-Output ('Waiting for project commandlet '+$inspectCommandlet.ProcessId)
        try { Wait-Process -Id $inspectCommandlet.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
    }
}
if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") {
    & 'D:\FPS3D\FPSGAME\Tools\AssetPipeline\mcp_call_codex.ps1' `
        -PythonScript (Join-Path $PSScriptRoot 'import_assets.py') `
        -OutputFile (Join-Path $PSScriptRoot 'import-bridge-01.txt') `
        -QueueWaitSeconds 300 -RequestTimeoutSeconds 300 -MaxOutputChars 1800
} else {
    & (Join-Path $PSScriptRoot 'import_background.ps1')
}
