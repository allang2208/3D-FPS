M4 firing sound revision, 2026-09-14.

Source: original M4HK416AudioEmpty20260909/Audio/fire.wav, user-owned/source rights unchanged. This is not a new CC0 asset.

Authoring: ../punch_m4.py. Initial impact +2.5 dB, smooth attack return by 45 ms; gentle parallel 100-200 Hz body boost and 280-480 Hz reduction; tail tapered to -3.5 dB by 200 ms without truncation. Linked stereo soft knee preserves headroom. Original pitch, duration and four subtle decay variations retained.

Import: Tools/AssetPipeline/import_m4_punch.py replaces the four currently referenced M4OriginalAudio20260913 SoundWaves. Previous uassets retained in PreviousAssets; previous WAV variants remain in ../M4OriginalVariants. Existing runtime gain and concurrency are unchanged. Mechanical sounds, QBZ191 and suppressed bank are unchanged. Environment ducking is deferred until in-game masking is reported, as proposed.

No listening/game tests performed for this revision; user will audition.
