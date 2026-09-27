# Reference-video original audio — 2026-09-26

The user rejected the previous edited cues and again requested the actual draw/release sounds from https://www.bilibili.com/video/BV1jGdDBkEkc/ (StarLord星小爵, APEX Bocek showcase).

This revision uses the existing reference interval `../BowVideoAudio20260926/reference_32_49.wav`. Draw: video 37.450–38.150 s; release: 36.772–37.205 s. It retains the source stereo mix, original rate/pitch, natural relative level and release tail. Only 1–15 ms edit-boundary fades are applied; there is no mono conversion, noise-removal filter, peak boost, time stretching or synthesis. These are video-mix excerpts, not isolated original game stems.

`author_audio.py` produces the two WAVs and the reproducible source/processing manifest. `import_audio.py` imports and saves two separate SoundWaves in `/Game/Weapons/DarkBow20260925/AudioVideoDirect20260926`. An actual `import-receipt.json` containing `saved: true` records asset completion.

The bow's `bow_audio_original_speed = 1` disables duration-based draw pitch and charge-based release pitch. Both original cues use the same 0.6 runtime volume multiplier. The draw plays once at draw entry and naturally ends after 0.7 seconds, even if the gameplay draw action lasts longer; cancellation and release still stop its voice. It does not change animation duration or weapon statistics.

The media, WAVs and SoundWave packages are local user-requested excerpts. No asset redistribution license was supplied; they are not CC0. Do not publish audio bytes or source packages with source-code releases. No audio audition or gameplay test was performed or claimed.
