# AKM user-selected video audio

## Magazine insertion timing adjustment

User reports insertion audio is early for all three AKM magazines. The shared
AKM MagInsert event is delayed by 0.18 source-animation seconds before mapping to
runtime reload speed. Normal reload: 1.233333 -> 1.413333; empty reload:
1.150000 -> 1.330000. This is an initial feedback-based adjustment, not a measured
contact-frame validation. MagSeat, charging, drum removal and animation timing
are unchanged. No audition or gameplay test.

Source: https://www.bilibili.com/video/BV17VtT6REZr/ (LAZERH).
User requested the fire sound near 6:12 and reload/charging at 6:17–6:19.
The nearby isolated shot is cut at 373.040–373.435 seconds, before the following shot.
Reload/charging fragments stay inside 377.000–378.460 seconds and are adapted to
AKM's existing MagOut, MagInsert, MagSeat, ChargePull and ChargeRelease contacts.
Role assignment is an editorial adaptation from source imagery/transients.

`author_audio.py` makes 48 kHz stereo PCM16 assets with short edge fades. No pitch
change or extra loudness processing. The source is a mixed video soundtrack;
background sound is not claimed to have been separated. `provenance.json` records
exact source cuts. Third-party rights remain with their owners; no redistribution
license is established. Original media and generated WAV/uasset stay local.

`import_audio.py` creates `/Game/Weapons/AKM/VideoAudio20260921` SoundWaves, copying
the existing AKM playback settings. Original assets are retained. `LoadAKMSound`
selects these six assets only for the AKMSoviet viewmodel; other weapons keep their
original routing, including shared charging sounds. Suppressed fire, equip and dry
click are unchanged. DefaultGame.ini includes the new folder in cooking.

No audition, PIE, runtime or packaging test. Import receipt and Live Coding output
record production operations only. Re-equip AKM / start a new game instance after
successful Live Coding to reload references. A later normal Editor build is still
needed to bake native changes into the base DLL.

## Publication status (2026-09-21)

AKM Editor build subsequently returned Succeeded (target up to date). The user accepted AKM normal fire/reload and insertion timing before requesting suppressed fire. AKM suppressed audio is separate under AKMSuppressedAudio20260921. Later A762/PKM routing extensions belong to their weapon integration tasks. Earlier build/Live Coding limitations above describe historical attempts. No new runtime test performed for publication.
