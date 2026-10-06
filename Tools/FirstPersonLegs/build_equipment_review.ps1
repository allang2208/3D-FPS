param([switch]$CompileOnly)
$ErrorActionPreference='Stop'
$outfitProject='D:/FPS3D/FPSGAME'
$outfitOutput="$outfitProject/SourceAssets/EquipmentReview20261006"
$outfitGate=[Threading.Mutex]::new($false,'Local\CodexUeMcp-Port-8000')
$outfitHeld=$false
try {
    try { $outfitHeld=$outfitGate.WaitOne([TimeSpan]::FromSeconds(300)) } catch [Threading.AbandonedMutexException] { $outfitHeld=$true }
    if(-not $outfitHeld){throw 'Existing UE batch remains active.'}
    $outfitDeadline=[DateTime]::UtcNow.AddMinutes(40)
    while($true){
        $outfitProcesses=Get-CimInstance Win32_Process
        if(-not $CompileOnly -and ($outfitProcesses | Where-Object { $_.Name -in @('UnrealEditor.exe','FPSGAME.exe') -and $_.CommandLine -match 'FPSGAME' })){
            throw 'FPSGAME is open; preserve the session until the user saves and closes it.'
        }
        if(-not ($outfitProcesses | Where-Object { ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool') -or ($_.Name -eq 'UnrealEditor-Cmd.exe' -and $_.CommandLine -match 'FPSGAME') })){break}
        if([DateTime]::UtcNow -gt $outfitDeadline){throw 'Existing build/commandlet remains active.'}
        Start-Sleep -Seconds 10
    }
    $outfitLabel=if($CompileOnly){'objects'}else{'editor'}
    $outfitArgs=@('FPSGAMEEditor','Win64','Development',"-Project=$outfitProject/FPSGAME.uproject",'-NoHotReload','-NoHotReloadFromIDE','-NoUBA','-NoUbaLocal','-MaxParallelActions=1',"-Log=$outfitOutput/build-$outfitLabel.log")
    if($CompileOnly){$outfitArgs+='-NoLink'}
    & 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' @outfitArgs *> "$outfitOutput/build-$outfitLabel-console.txt"
    if($LASTEXITCODE -ne 0){throw "Equipment review build failed; see build-$outfitLabel.log"}
    Write-Output "EQUIPMENT_REVIEW_BUILT $outfitLabel"
} finally {if($outfitHeld){$outfitGate.ReleaseMutex()};$outfitGate.Dispose()}
