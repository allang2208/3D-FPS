# Repro and first failure candidates
User reports standard curved magazine insertion clipping and weak final empty-reload slap. Expected: hand clears magazine/receiver for full insertion and release; clear visible impact.
Current editor PID 41756 loads module 2026091071. Its DLL contains M4ReloadPolish animation reference. Live editor ObjectTools reads reload 505 sampled keys, 2.1 s. Previous version was applied.
Hypotheses: (1) old test only covered insertion middle, missing grasp/release transitions; (2) signed contact solver misses glove edges/receiver; (3) slap path is fast but lacks screen-visible anticipation and receiver reaction; (4) runtime blend, check action alpha around contacts.
Evidence: whole-action mesh sweeps, key pose and runtime images, complete source and sound timing, new gameplay captures. Preserve current drum work and user editor.
