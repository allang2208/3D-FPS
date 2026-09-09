# Weather Asset Notices

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
- Use: Deferred-decal puddle material placed on traced outdoor surfaces during rain.

## Niagara Examples Pack

- Creator: Epic Games
- Source: https://www.fab.com/listings/0e188eca-4e54-4fb2-a9ed-d8b8a565e600
- Use: Reference content for Niagara authoring and scalability review. The FPS weather manager uses its own lightweight rain and splash systems rather than loading the example maps at runtime.
