param([switch]$SkipBuild,[string]$Manifest='native_manifest.json',[string]$OutputName='Native')
$ErrorActionPreference='Stop'
$reviewGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$reviewHeld=$false
try {
    try {$reviewHeld=$reviewGate.WaitOne([TimeSpan]::FromMinutes(15))} catch [Threading.AbandonedMutexException] {$reviewHeld=$true}
    if(-not $reviewHeld){throw 'UE asset queue occupied; no changes made.'}
    $reviewDeadline=[DateTime]::UtcNow.AddMinutes(15)
    do {
        $reviewBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'UnrealEditor-Cmd.exe' -or $_.Name -eq 'cl.exe' -or $_.Name -eq 'link.exe' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        })
        if($reviewBusy) {
            if([DateTime]::UtcNow -ge $reviewDeadline){throw 'Existing build or commandlet remains occupied.'}
            try {[void][Diagnostics.Process]::GetProcessById($reviewBusy[0].ProcessId).WaitForExit(45000)} catch [ArgumentException] {}
        }
    } while($reviewBusy)
    if(Get-CimInstance Win32_Process -Filter "Name='UnrealEditor.exe'" | Where-Object {[string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'FPSGAME.uproject'}) {
        throw 'FPSGAME editor is open; preserving its process and assets.'
    }
    if(-not $SkipBuild) {
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -NoHotReloadFromIDE *> "$PSScriptRoot/native-build.log"
        if($LASTEXITCODE -ne 0){throw 'Native review tool build failed; see native-build.log.'}
    }
    $reviewOutput="$PSScriptRoot/$OutputName"
    [void][IO.Directory]::CreateDirectory($reviewOutput)
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=M24HoldReview "-SurfaceManifest=$PSScriptRoot/$Manifest" "-Output=$reviewOutput" -unattended -nop4 -nosplash -nosound -AllowCommandletRendering -RenderOffscreen -d3d12 "-abslog=$reviewOutput/capture.log" *> "$reviewOutput/capture.stdout.txt"
    if($LASTEXITCODE -ne 0){throw 'Native M24 review failed; see native-capture.log.'}
    Write-Output 'M24 native surface capture completed.'
} finally {
    if($reviewHeld){$reviewGate.ReleaseMutex()}
    $reviewGate.Dispose()
}
