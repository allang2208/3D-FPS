# Free footsteps and water movement — 2026-09-13

User listening revision: Grass now uses the existing `S_mud02` dirt recording instead of `S_leaves01/02`. Stride, volume and surface detection are unchanged; original leaf assets remain available. Not auditioned or game-tested by the agent.

## Sources

- AutoFootstep by Metaseven / suramaru517: https://github.com/suramaru517/AutoFootstep . CC0-1.0; original LICENSE retained in Plugins/AutoFootstep. Installed source plus editor animation modifier. Runtime uses its loaded `AutoFootstepEffectContext` playback API; FPS triggering is implemented separately because the first-person viewmodel does not provide leg contact animation.
- TinyWorlds: https://opengameart.org/content/different-steps-on-wood-stone-leaves-gravel-and-mud . CC0. Eight recordings for wood, stone, leaves, gravel and mud.
- Peludo: https://opengameart.org/content/water-splash-and-sand-footsteps . CC0. Two bucket-water splash recordings, adapted for shallow/deeper movement, not claimed as actual swimming recordings. Author requests an itch.io reference; the publication does not supply an itch.io URL, so the named author and source publication are retained here.

No purchase, Fab download, or commercial sound library was used. The previously discussed Sound Kajiya Fab library is not installed. The audio source files, archives and reproducible `prepare.py` remain in this directory; `manifest.json` records source hashes and audio mappings. WAVs are 48 kHz mono PCM16, with high-pass filtering, short fades and matched peaks. Deep-water variants are filtered versions of the two splash recordings.

## Integration

`UFPSFootstepAudioComponent` is a default player component. It runs locally at 30 Hz, accumulating real horizontal distance; standing, blocked movement, airborne movement outside water and teleport jumps do not generate walking steps. Run/crouch stride and volume differ; landing adds one contact cue. Multiple-sample banks avoid immediate repeats; one-sample banks use slight pitch/gain variation.

Ground selection uses named physical surfaces matching bank names, then physical material/component/material names. Wood, stone, gravel, dirt and grass/leaves are provided. Default hard floors use Stone, temperate terrain uses Grass. Metal and snow currently use the default bank unless configured; these are not separate recordings in this free set.

Current custom temperate rivers use the existing river plan plus capsule-bottom height: shallow water blends a quiet bed contact with splash, deeper water uses filtered splashes, entry/exit add a splash. Elevated bridge contact stays dry. Character swimming mode uses water movement cues but this component does not create swimming physics. Other water implementations need their water-height adapter; rendering a blue surface alone does not establish water detection.

Edit the FootstepAudio component's Volume, WalkStrideCm, RunStrideCm, CrouchStrideCm and Banks in character defaults to tune. Sound assets: `/Game/Audio/FreeFootsteps`. Import tool: `Tools/AssetPipeline/import_free_footsteps.py`.

Restart the editor after compilation to load the new plugin and character component. No audition, PIE, screenshots, regression or gameplay acceptance was performed. User testing remains pending.
