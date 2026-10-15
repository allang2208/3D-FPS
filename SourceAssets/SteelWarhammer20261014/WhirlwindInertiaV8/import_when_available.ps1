$ErrorActionPreference='Stop'
while($armBuilds=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool' })) {
    foreach($armBuild in $armBuilds) {
        Write-Output ('Waiting for active UBT process '+$armBuild.ProcessId)
        try { Wait-Process -Id $armBuild.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
    }
}
while($armCommandlets=@(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor-Cmd.exe'" | Where-Object { $_.CommandLine -match 'FPSGAME' })) {
    foreach($armCommandlet in $armCommandlets) {
        Write-Output ('Waiting for project commandlet '+$armCommandlet.ProcessId)
        try { Wait-Process -Id $armCommandlet.ProcessId -ErrorAction Stop } catch [Microsoft.PowerShell.Commands.ProcessCommandException] { }
    }
}
if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'") {
    & 'D:\FPS3D\FPSGAME\Tools\AssetPipeline\mcp_call_codex.ps1' `
        -PythonScript (Join-Path $PSScriptRoot 'import_assets.py') `
        -OutputFile (Join-Path $PSScriptRoot 'import-bridge-02.txt') `
        -QueueWaitSeconds 300 -RequestTimeoutSeconds 300 -MaxOutputChars 1800
} else {
    & (Join-Path $PSScriptRoot 'import_background.ps1')
}
