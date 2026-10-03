# Consumable swallow audio

Source recordings supplied by the user in `D:/FPS3D/资产/音效`:

- `吞咽水.mp3`, `吞咽水2.mp3`, `吞咽水3.mp3`: shared random water/potion and fountain refill sounds.
- `吞咽食物.mp3`: one swallow during the bread/baguette eating action.

`prepare_audio.py` decodes the recordings to 48 kHz stereo, 16-bit PCM WAV without changing their volume, speed or duration. `import_audio.py` imports and saves four non-looping SoundWave assets under `/Game/Audio/Consumables20261003` with inline loading. The original MP3 files are preserved in their source directory.

`UFPSPotionUseComponent` loads the four sounds with its existing asynchronous preload. Its current animation clock begins playback at `DrinkStart`. Water swallows are selected randomly for each play, separated by the selected clip's duration plus 0.12–0.20 seconds. A bounded timer ends the sequence at `DrinkEnd`; cancel and owner destruction stop it. Food plays the complete recording once, including its natural tail while the hand retracts.

The existing fountain interaction calls `PlayHydrationAudio()` after successful hydration. Other refill actions can use this Blueprint/C++ API: zero duration plays one random sample, and a positive duration randomly repeats water samples over that interval.

`build_and_import.ps1` waits for existing editor/build processes, builds the normal Editor/Game targets, and uses a headless Python commandlet to import and save assets. It never stops another process or starts editor UI, gameplay, or tests. `import_receipt.json` records actual asset saves; source scripts alone do not imply assets are installed.
