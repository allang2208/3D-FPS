# WitchRebuilt candidate

Editable authoring and FBX delivery for the sole WitchRebuilt variant.
Current stages: Seams07 / Drape07 geometry and cloth, Hands08 finger grips,
Fabric09 shared cloth (with the Revision11 graph fix), FlightDistance12,
and LiquidProjectile13 normal magic projectiles. The user accepted the overall
rebuilt model; the latest projectile visuals and distance behavior remain untested.
Status: `../../Docs/Monsters/witch-rebuilt-20260922.md`.
Publication, local recovery inputs and archive boundaries:
`../../Docs/Monsters/witch-publication-20260923.md`.

Sources are retained locally:
- Full anatomical skin: `../WitchMeshy20260919/Authoring/LayeredV04/Sources/Nurse_SourceSkinWalk.fbx`, material 3. Existing licensed Zombie Female asset; entire neck-down body, no limb cut.
- Target skeleton/carry: `../WitchFoundation20260920/Sources/Quinn.fbx` and existing Idle/Walk authoring. Epic project assets.
- Witch identity/UV/PBR: `../WitchMeshy20260919/Authoring/CleanRobeV06/Witch_CleanRobeV06.blend`.
- Clean gestures: original `CloudGripV02` CastPoison, ThrowPoisonBottle, DeathBackward. Fixed business clock; source motion adapted to new anatomy, fingers added locally.
- Original sprite/config references: `../WitchMeshy20260919/Reference/Original`.

Do not publish library binaries. No external Github addon was installed/executed.
Authoring tools: `../../Tools/WitchRebuilt`. Blender 5.1.2. Existing per-revision
`Before` inputs used by the authoring scripts remain here; they are not disposable
automatic backups. Rejected MeshLab experiments and unused `.blend1` saves moved
to `../../trash/witch-rebuilt-publication-20260923` with a SHA-256 manifest.
Do not run all historical scripts in sequence over current accepted assets.
