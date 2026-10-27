$ErrorActionPreference='Stop'
$piercingRoot='D:/FPS3D/FPSGAME'
$piercingOutput="$piercingRoot/Saved/HeartPiercingArrowAudio20261026"
New-Item -ItemType Directory -Force -Path $piercingOutput | Out-Null

function Wait-ForBuild {
    $piercingDeadline=[DateTime]::UtcNow.AddMinutes(20)
    $piercingAnnounced=$false
    while($true) {
        $piercingBusy=@(Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or
            ($_.Name -eq 'cmd.exe' -and $_.CommandLine -match 'Build.bat')
        })
        if(-not $piercingBusy.Count) { return }
        if(-not $piercingAnnounced) { Write-Output 'Waiting for the active build to finish before submitting.'; $piercingAnnounced=$true }
        if([DateTime]::UtcNow -ge $piercingDeadline) { throw 'Active build preserved; this build was not submitted.' }
        Start-Sleep -Seconds 5
    }
}

foreach($piercingTarget in @('FPSGAMEEditor','FPSGAME')) {
    Wait-ForBuild
    $piercingGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
    $piercingHeld=$false
    try {
        try { $piercingHeld=$piercingGate.WaitOne([TimeSpan]::FromMinutes(10)) }
        catch [Threading.AbandonedMutexException] { $piercingHeld=$true }
        if(-not $piercingHeld) { throw 'UE batch occupied; build not started.' }
        $piercingOwners=@(Get-CimInstance Win32_Process | Where-Object {
            if($piercingTarget -eq 'FPSGAMEEditor') {
                $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -and (-not $_.CommandLine -or $_.CommandLine -match 'FPSGAME')
            } else { $_.Name -match '^FPSGAME(-Win64-.+)?\.exe$' }
        })
        if($piercingOwners.Count) { throw "Running binary owner preserved; cannot build $piercingTarget." }
        $piercingLog="$piercingOutput/build-$piercingTarget.log"
        $piercingStdout="$piercingOutput/build-$piercingTarget-stdout.log"
        Write-Output "Building $piercingTarget."
        & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' $piercingTarget Win64 Development "-Project=$piercingRoot/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -NoUBA -MaxParallelActions=4 "-Log=$piercingLog" *> $piercingStdout
        $piercingExit=$LASTEXITCODE
        @{target=$piercingTarget;exit_code=$piercingExit;log=$piercingLog;runtime_tested=$false;editor_started=$false} | ConvertTo-Json | Set-Content -LiteralPath "$piercingOutput/build-$piercingTarget.json" -Encoding utf8
        Get-Content -LiteralPath $piercingStdout -Tail 14
        if($piercingExit -ne 0) { throw "Build failed with exit $piercingExit. See $piercingLog" }
    } finally {
        if($piercingHeld) { $piercingGate.ReleaseMutex() }
        $piercingGate.Dispose()
    }
}
