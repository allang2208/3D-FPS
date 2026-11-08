param()
$ErrorActionPreference='Stop'
$iconProject='D:/FPS3D/FPSGAME'
$iconOutput=Join-Path $PSScriptRoot 'Artwork'
[IO.Directory]::CreateDirectory($iconOutput) | Out-Null
$iconGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$iconHeld=$false
try {
    # Read-only production commandlet: no package saves, player profile or map.
    # Its standalone catalog API is not exposed to the editor Python bridge.
    while(-not $iconHeld){
        try{$iconHeld=$iconGate.WaitOne(10000)}catch [Threading.AbandonedMutexException]{$iconHeld=$true}
        if(-not $iconHeld){continue}
        $iconBusy=@(Get-CimInstance Win32_Process | Where-Object {
            $_.Name -in @('cl.exe','link.exe','UnrealBuildTool.exe') -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME')
        })
        if($iconBusy.Count){$iconGate.ReleaseMutex();$iconHeld=$false;Start-Sleep -Seconds 10}
    }
    $iconStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
    $iconLog=Join-Path $PSScriptRoot "m249-production-$iconStamp.log"
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' "$iconProject/FPSGAME.uproject" -run=ColdSteelWeaponIconCatalog -Definition=ue_m249 "-OutputDirectory=$iconOutput" -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nop4 -nosplash -nosound -Multiprocess '-ini:EditorPerProjectUserSettings:[/Script/ModelContextProtocolEngine.ModelContextProtocolSettings]:bAutoStartServer=False' "-abslog=$iconLog" *> "$iconLog.console.txt"
    $iconExit=$LASTEXITCODE
    $iconText=Get-Content -LiteralPath $iconLog -Raw -Encoding utf8
    $iconComplete=$iconText -match 'WeaponIconCatalog: wrote .*ue_m249.png' -and $iconText -match 'WeaponIconCatalog: COMPLETE failures=0'
    @{exit_code=$iconExit;catalog_complete=$iconComplete;log=$iconLog;output="$iconOutput/ue_m249.png";runtime_tested=$false} | ConvertTo-Json | Set-Content -LiteralPath "$PSScriptRoot/m249-authoring.json" -Encoding utf8
    if(-not $iconComplete -or $iconExit -notin @(0,1)){throw "M249 catalog production did not complete: $iconLog"}
    Write-Output "M249_INVENTORY_ARTWORK_WRITTEN $iconOutput/ue_m249.png"
} finally {if($iconHeld){$iconGate.ReleaseMutex()};$iconGate.Dispose()}
