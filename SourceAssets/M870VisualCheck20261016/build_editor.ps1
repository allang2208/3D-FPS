$ErrorActionPreference='Stop'
$taskRoot='D:/FPS3D/FPSGAME/SourceAssets/M870VisualCheck20261016'
$taskGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$taskHeld=$false
try {
    while(-not $taskHeld) {
        $native=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('cl.exe','link.exe','UnrealBuildTool.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if($native.Count){Start-Sleep -Seconds 15;continue}
        try {$taskHeld=$taskGate.WaitOne(30000)} catch [Threading.AbandonedMutexException] {$taskHeld=$true}
        if($taskHeld) {
            $native=@(Get-CimInstance Win32_Process | Where-Object {
                $_.Name -in @('cl.exe','link.exe','UnrealBuildTool.exe') -or
                ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
            })
            if($native.Count){$taskGate.ReleaseMutex();$taskHeld=$false;Start-Sleep -Seconds 15}
        }
    }
    & 'D:/FPS3D/FPSGAME/Tools/Build/Build-Editor.ps1' *> "$taskRoot/build_editor.log"
    @{target='FPSGAMEEditor Win64 Development';succeeded=$true;runtime_tested=$false;log="$taskRoot/build_editor.log"} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/build_receipt.json" -Encoding utf8
} catch {
    @{target='FPSGAMEEditor Win64 Development';succeeded=$false;error=$_.Exception.Message;runtime_tested=$false;log="$taskRoot/build_editor.log"} | ConvertTo-Json | Set-Content -LiteralPath "$taskRoot/build_receipt.json" -Encoding utf8
    throw
} finally {
    if($taskHeld){$taskGate.ReleaseMutex()};$taskGate.Dispose()
}
