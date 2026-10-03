# Waits until the tree builds (parallel-session WIP may block it for a while),
# then renders the ore vein preview PNG via the OreVeinPreview commandlet.
# The three rendering flags are REQUIRED: without -AllowCommandletRendering the
# commandlet never creates render-target resources (proven 2026-10-02).
# Output: Saved/OreVeinRocks/preview_all.png + orev preview log.
$ErrorActionPreference = 'Continue'
$build = 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat'
$cmdlet = 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe'

for ($attempt = 1; $attempt -le 40; $attempt++) {
    $editors = @(Get-Process UnrealEditor,UnrealEditor-Cmd -ErrorAction SilentlyContinue)
    if ($editors.Count -gt 0) { Write-Host "[ore-watcher] editors busy, retry in 60s"; Start-Sleep -Seconds 60; continue }
    Write-Host "[ore-watcher] attempt ${attempt}: building editor target"
    & $build 'FPSGAMEEditor' 'Win64' 'Development' -project='D:/FPS3D/FPSGAME/FPSGAME.uproject' -waitmutex > 'D:/FPS3D/FPSGAME/Saved/orewatch_build.log' 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[ore-watcher] build ok; rendering preview"
        & $cmdlet 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=OreVeinPreview -AllowCommandletRendering -RenderOffscreen -NoTextureStreaming -unattended -nosplash > 'D:/FPS3D/FPSGAME/Saved/orepreview_log.txt' 2>&1
        Write-Host "[ore-watcher] done; see D:/FPS3D/FPSGAME/Saved/OreVeinRocks/preview_all.png"
        exit 0
    }
    Write-Host "[ore-watcher] build failed (probably parallel WIP), retry in 60s"
    Start-Sleep -Seconds 60
}
Write-Host "[ore-watcher] gave up after 40 attempts"
exit 1
