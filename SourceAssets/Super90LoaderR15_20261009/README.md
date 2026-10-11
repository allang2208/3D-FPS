# Super90 loader R15

Preserve the user-accepted R14 full stroke, compress the drive from 48 to 36 source frames, and use seven original contact cuts from the supplied Delta Force recording only for the loader branch.

Production order: `prepare_timing.py` → Blender `author_r15.py`; `read_reference_audio.py` → `prepare_audio.py`; `run_r15.ps1` imports 15 animations, four grip profiles and seven sound waves. The timeline and audio scripts generate the corresponding C++ reference headers. Native runtime bindings are in `Super90SpeedloaderVisual.cpp` and `Super90SpeedloaderAssets.h`.

The audio is a derivative of the user's mixed recording, not isolated stems or newly recorded foley. Source provenance is in `audio_provenance.json`; no redistribution rights are inferred. Original standard reload audio is untouched.

See `Docs/Weapons/super90-speedloader-r15-audio-drive-20261009.md`. No game test or listening acceptance has been performed.
