# User video bow cues — 2026-09-26

Source: https://www.bilibili.com/video/BV1jGdDBkEkc/ — StarLord星小爵, 【APEX英雄】波赛克S28赛季进化皮展示-大人物.

The user specifically requested replacing the local bow sounds with the draw/release sounds in this video. `acquire_audio.py` obtains the public audio interval 32–49 seconds for local editing; `author_audio.py` cuts handling, engagement, draw and release cues. Exact ranges and processing are in `audio-manifest.json`. `import_audio.py` creates four new SoundWave assets under `/Game/Weapons/DarkBow20260925/AudioVideo20260926` and saves only those assets.

The original reference, derived WAVs and imported SoundWaves are local third-party excerpts. No source-asset redistribution license was supplied. They are not CC0 and do not inherit the former Still North library's license. Do not publish the reference audio, signed download metadata, WAVs or SoundWave source packages as open-source assets.

Selection used the reference video frames and audio transient envelopes. The available assistant media tool could not hear the audio; no audition or gameplay test is claimed. Background reduction is a soft spectral edit, not a claim of isolated original game sound stems. Final sound and placement acceptance belongs to the user.

The older CC0 assets remain available at their original paths for rollback, but the active bow configuration now references these four video cues.
