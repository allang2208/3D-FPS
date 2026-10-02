$ErrorActionPreference = 'Stop'
$taskSource = 'D:/FPS3D/资产/音效/撞门.mp3'
$taskFfmpeg = 'D:/FPS3D/FPSGAME/SourceAssets/M4Infima/PreviewTools/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe'
$taskCopy = Join-Path $PSScriptRoot 'Original.mp3'
$taskWav = Join-Path $PSScriptRoot 'S_DoorPushImpact.wav'
Copy-Item -LiteralPath $taskSource -Destination $taskCopy
& $taskFfmpeg -hide_banner -loglevel error -y -i $taskCopy -map 0:a:0 -vn -map_metadata -1 -ar 48000 -c:a pcm_s16le $taskWav
if ($LASTEXITCODE -ne 0) { throw 'User-provided door audio conversion failed.' }
$taskReceipt = [ordered]@{
    status = 'wav_authored_unreal_import_pending'
    date = '2026-10-02'
    source = $taskSource
    archived_source = $taskCopy
    source_origin = 'User-provided local MP3 selected for door impact replacement'
    license = 'User-provided; no third-party license claim assigned'
    source_sha256 = (Get-FileHash -LiteralPath $taskCopy -Algorithm SHA256).Hash.ToLowerInvariant()
    output = $taskWav
    output_sha256 = (Get-FileHash -LiteralPath $taskWav -Algorithm SHA256).Hash.ToLowerInvariant()
    output_sample_rate_hz = 48000
    output_channels = 'Preserved from source'
    output_bit_depth = 16
    crop = $false
    normalization = $false
    intended_unreal_asset = '/Game/Audio/Interactions/DoorPush20261002/S_DoorPushImpact.S_DoorPushImpact'
    intended_action_contact_seconds = 0.36
    runtime_volume_multiplier = 0.85
    audio_auditioned = $false
    game_tested = $false
}
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'production-receipt.json'), ($taskReceipt | ConvertTo-Json -Depth 8) + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
Write-Output 'User MP3 copied and converted to full-length PCM WAV; import pending.'
