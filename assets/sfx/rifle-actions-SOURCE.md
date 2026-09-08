# Rifle audio revision — 2026-09-08

## Newly acquired public sources

- `_Linus_Sebastian`, **ZM_098A_S03.wav**, https://freesound.org/people/_Linus_Sebastian/sounds/493876/ . Page describes an AK-47 shot and tags WASR-AK-47 / 7.62x39mm; CC0 1.0. This is an AK-family reference for the game's AKM, not a verified recording of the exact modeled variant. Public HQ MP3 preview downloaded from https://cdn.freesound.org/previews/493/493876_10603899-hq.mp3 into `akm_classic/source/`; original login-gated WAV was not acquired.
- `serøutōnin--deprivəd`, **AK-47 Assault Rifle being unloaded and reloaded**, https://freesound.org/people/ser%C3%B8ut%C5%8Dnin--depriv%C9%99d/sounds/674742/ . CC0 1.0. Author explicitly describes mixing recordings of their own airsoft weapons. Used as mechanical Foley, not advertised as a real AKM recording. Public HQ MP3 https://cdn.freesound.org/previews/674/674742_7157894-hq.mp3 retained in `akm_classic/source/`; original WAV not acquired.
- `SpringySpringo`, **Gun reload sounds**, https://opengameart.org/content/gun-reload-sounds . CC0, author-recorded airsoft sounds. Original public WAV https://opengameart.org/sites/default/files/assaultriflereload1_0.wav retained as `qbz191/source/assaultriflereload1.wav`. Used as rifle Foley for QBZ191; not a QBZ191 field recording.

CC0 deed: https://creativecommons.org/publicdomain/zero/1.0/ . Pages checked 2026-09-08. Optional author attribution is retained here. No account-gated download bypass was used.

## Existing sources retained

- AK105: `reload_sharp.mp3`; HK416: `hk416/reload.mp3`. Their original recordings remain intact; newly cut mechanics inherit the existing upstream rights. This work does not assign CC0 to them.
- Short charging/release fallback cues use wadaltmon's CC0 AR15 Various Sounds, already documented in `m16/SOURCE.md`. These small mechanical cues remain shared where a dedicated recording is absent. M16's authored event table is retained.
- HK416, M16, QBZ191 and AK105 firing selections and equipment sounds remain unchanged. AKM equipment still uses the existing AK-family recording. This revision removes duplicate AKM **reload** and HK416/QBZ191 **reload** playback, not every shared short cue in the project.

## Editing and runtime

`tools/prepare_rifle_audio.py` preserves originals and generates 13 mechanical mono 44.1 kHz / PCM16 clips. `rifle-actions-edit-report.json` records source cuts and output peaks. Mechanics are band-limited, faded and peak-normalized. The rejected firing cut is no longer generated. No pitch-shift or synthetic blast layer is added.

`scripts/rifle_reload_audio.gd` schedules events in source-animation seconds. The same `large_drum_reload.output_time` transformation used by the animation moves events for the drum; effective gameplay duration then sets clock speed. Short sounds retain pitch 1.0. Repeated reload input cannot restart playback, holstering cancels cues and active tails, and cached viewmodels retain their audio players. Old full reload recordings remain available as source/fallback resources but are not overlaid on the five-rifle event route.


## 2026-09-08 user selection supersedes AKM firing candidate

AKM normal firing now shares assets/sfx/akm_burst.mp3 with AK105 at the user's explicit request. The rejected akm_classic/fire.wav and its 493876 preview source are archived under E:/无尽轮回/3d/trash/audio-20260908/. Reload event timing and the separately selected suppressor sound are unchanged.

## Public checkout subset

This public commit includes only the two CC0 mechanical sources and six cuts for akm_classic/qbz191. Rebuild with `python tools/prepare_rifle_audio.py --weapons akm_classic qbz191`. The 13-cut description above refers to the complete local game. HK416/AK105 dedicated cuts and the Sonniss suppressor recording are not redistributed. Missing dedicated cues use the existing M16 CC0 bank. See docs/rifle-audio-publication-20260908.md for integration status.
