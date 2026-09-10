# Weather Asset Notices

## 2026-09-10 source snapshot

No Fab/engine binary assets, `.uasset` files or editable third-party maps are
redistributed in this snapshot. Previews show the integrated project; source
and configuration scripts document the local implementation.

Dynamic Sky & Light Manager (`/Game/PWL_Light_Manager`), Unreal Normandy and
MilitaryTrench remain separately acquired local dependencies under their
respective licenses. Their presence locally does not grant permission to
repackage their source assets. The engine SimpleVolumetricCloud material is
referenced by path and must come from the user's Unreal installation.

Rain/wet-surface material code is procedural project-authored code. Niagara
configuration scripts require the four existing local emitter graphs; those
graphs and any embedded template dependencies are not published here.

The following Fab assets are used by the FPSGAME weather system.

## Migrated Rain Loops

- `S_Rain_Light_Loop`: derived from Freesound 497044, "Rain on leaves,ground garden" by spok13, licensed under CC BY 3.0. Source: https://freesound.org/people/spok13/sounds/497044/
- `S_Rain_Soft_Loop` and `S_Rain_Patter_Loop`: original procedural audio generated for the previous Godot project; no third-party samples.
- Use: crossfaded light, medium, and heavy rain layers, attenuated while the player is under shelter.

## Free Thunder Sounds

- Creator: Gregor Quendel - Cinematic Sound Design
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Source: https://www.fab.com/listings/c832a656-f75c-45fc-bdb1-8fb702a7ba90
- Use: Randomized thunder playback after storm lightning flashes.

## Simple Water Puddles (Free)

- Creator: JVAD3D Models
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Source: https://www.fab.com/listings/5718b8ac-27f7-4741-85ba-2cff7bf2f77d
- Historical use: Deferred-decal puddle material in the 2026-09-09 baseline.
  The 2026-09-10 weather runtime uses the project-authored M_RainWetSurface;
  the shared JVAD3D pack is retained locally for any other users.

## Niagara Examples Pack

- Creator: Epic Games
- Source: https://www.fab.com/listings/0e188eca-4e54-4fb2-a9ed-d8b8a565e600
- Use: Reference content for Niagara authoring and scalability review. The FPS weather manager uses its own lightweight rain and splash systems rather than loading the example maps at runtime.
