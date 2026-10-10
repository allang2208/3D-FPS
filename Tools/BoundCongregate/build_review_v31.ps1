param([switch]$AssetsOnly,[switch]$BuildOnly)
$ErrorActionPreference='Stop'
$bcProject='D:/FPS3D/FPSGAME'
$bcEngine='E:/Program Files (x86)/UE_5.8/Engine'
$bcOutput=Join-Path $bcProject 'SourceAssets/BoundCongregateMeshy20261006/ReviewV31'
function Wait-BCBuildWindow {
    $bcNotice=$false
    while($true) {
        $bcProcesses=Get-CimInstance Win32_Process
        $bcGui=$bcProcesses | Where-Object { $_.Name -eq 'UnrealEditor.exe' }
        if($bcGui) { throw 'A running editor must retain its loaded assets. Resume V31 using the editor bridge.' }
        $bcBusy=$bcProcesses | Where-Object {
            $_.Name -match '^(UnrealEditor-Cmd|FPSGAME.*|cl|link|UnrealBuildTool)\.exe$' -or
            ($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'UnrealBuildTool')
        }
        $bcLocked=$false
        $bcDll=Join-Path $bcProject 'Binaries/Win64/UnrealEditor-FPSGAME.dll'
        if(Test-Path -LiteralPath $bcDll) {
            try { $bcStream=[IO.File]::Open($bcDll,'Open','ReadWrite','None'); $bcStream.Dispose() }
            catch { $bcLocked=$true }
        }
        if(!$bcBusy -and !$bcLocked) { return }
        if(!$bcNotice) { Write-Output 'Waiting for the current native build/asset process to release the build window.'; $bcNotice=$true }
        Start-Sleep -Seconds 10
    }
}
if(!$AssetsOnly) {
    foreach($bcTarget in @('FPSGAMEEditor','FPSGAME')) {
        Wait-BCBuildWindow
        Write-Output "Building $bcTarget for V31"
        & "$bcEngine/Build/BatchFiles/Build.bat" $bcTarget Win64 Development "-Project=$bcProject/FPSGAME.uproject" -NoHotReload -NoHotReloadFromIDE -MaxParallelActions=4 "-Log=$bcOutput/build-$bcTarget.log" *> "$bcOutput/build-$bcTarget-console.log"
        if($LASTEXITCODE -ne 0) { throw "Build failed: $bcTarget. See the V31 build log." }
        Write-Output "Built $bcTarget"
    }
}
