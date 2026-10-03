param(
    [string]$OutputDirectory = 'D:\FPS3D\FPSGAME\SourceAssets\BlindSupplicantM07Meshy20261001\Audio',
    [string]$PythonExecutable = 'E:\无尽轮回\长期备份\2026-7-13-1\ComfyUI\.venv\Scripts\python.exe'
)

$ErrorActionPreference = 'Stop'
$taskAudioDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
[System.IO.Directory]::CreateDirectory($taskAudioDirectory) | Out-Null
$taskRawPath = Join-Path $taskAudioDirectory 'M07_WallMimic_RawHuihui.wav'
$taskMetaPath = Join-Path $taskAudioDirectory 'tts_source.json'
$taskSpeech = $null
$taskStream = $null

try {
    $taskSpeech = New-Object -ComObject SAPI.SpVoice
    $taskChineseVoices = @($taskSpeech.GetVoices() | Where-Object {
        ($_.GetAttribute('Language') -split ';') -contains '804'
    })
    if ($taskChineseVoices.Count -eq 0) {
        $taskBlocked = [ordered]@{
            stage = 'blocked_no_installed_simplified_chinese_sapi_voice'
            source_text = '有人吗……救救我……'
            runtime_tested = $false
            audio_played = $false
            engine_imported = $false
        }
        $taskBlocked | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskAudioDirectory 'audio_production.json') -Encoding UTF8
        throw 'No installed Simplified Chinese SAPI voice. Audio authoring preserved without synthesizing substitute speech.'
    }
    $taskVoice = $taskChineseVoices | Where-Object { $_.GetDescription() -match 'Huihui' } | Select-Object -First 1
    if ($null -eq $taskVoice) { $taskVoice = $taskChineseVoices[0] }
    $taskSpeech.Voice = $taskVoice
    $taskSpeech.Rate = -3
    $taskSpeech.Volume = 100

    $taskStream = New-Object -ComObject SAPI.SpFileStream
    # SAFT44kHz16BitMono = 34, SSFMCreateForWrite = 3.
    $taskStream.Format.Type = 34
    $taskStream.Open($taskRawPath, 3, $false)
    $taskSpeech.AudioOutputStream = $taskStream
    $taskXml = '<silence msec="380"/>有人吗<silence msec="950"/>救救我<silence msec="600"/>'
    # SPF_IS_XML = 8. The synchronous voice output is the file stream, never speakers.
    [void]$taskSpeech.Speak($taskXml, 8)
    $taskStream.Close()
    $taskSourceMetadata = [ordered]@{
        stage = 'offline_tts_source_written'
        source_text = '有人吗……救救我……'
        source_xml = $taskXml
        raw_file = $taskRawPath
        provider = 'Windows installed Microsoft SAPI desktop voice'
        voice_name = $taskVoice.GetDescription()
        voice_token_id = $taskVoice.Id
        voice_language = $taskVoice.GetAttribute('Language')
        voice_vendor = $taskVoice.GetAttribute('Vendor')
        sapi_voice_rate = -3
        requested_sample_rate_hz = 44100
        requested_channels = 1
        requested_pcm_bits = 16
        use_scope = 'Temporary local internal FPSGAME prototype; not final actor performance.'
        redistribution_license_reviewed = $false
        network_used = $false
        real_person_voice_cloned = $false
        audio_played = $false
        runtime_tested = $false
        engine_imported = $false
        created_utc = [DateTime]::UtcNow.ToString('o')
    }
    $taskSourceMetadata | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskMetaPath -Encoding UTF8
}
finally {
    if ($null -ne $taskStream) {
        try { $taskStream.Close() } catch { }
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($taskStream)
    }
    if ($null -ne $taskSpeech) {
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($taskSpeech)
    }
}

& $PythonExecutable (Join-Path $PSScriptRoot 'author_mimic_audio.py') --audio-dir $taskAudioDirectory
if ($LASTEXITCODE -ne 0) { throw "M07 offline audio processing failed with exit code $LASTEXITCODE." }
