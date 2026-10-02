# Floating mechanical sight diagnosis

## Repair requested after diagnosis

The user authorized the repair after live ownership was captured. Changes are
limited to `Source/FPSGAME/Weapons/M4FoldingSights.cpp` and
`Source/FPSGAME/Weapons/M4GunsmithVisual.cpp`:

- Both sight-creation branches initialize visibility from the retained rifle
  mesh and `bInventoryWeaponReady` before registering the new components.
- `UpdateFoldingSights` synchronizes all existing heads with that same state,
  including a partial pair, before updating the folding transforms.
- The gunsmith optic setter no longer overwrites this visibility using only
  the weapon-family and inventory flags.

The condition requires an equipped firearm, a visible rifle viewmodel and a
viewmodel that is not hidden in game. The shared path covers M4, QBZ191, A762
and LMG201. Meshes, mounts, folding angles, animation, materials and equipment
data are unchanged. No assets require import or resaving for this C++ repair.

Runtime tests remain for the user. No editor or game was launched or stopped
to apply the source changes.

The ordinary `FPSGAMEEditor Win64 Development` build completed successfully
using `Tools/Build/Build-Editor.ps1`, including compilation of both changed
source files and linking `Binaries/Win64/UnrealEditor-FPSGAME.dll`. This is a
base module build, not a Live Coding patch. Build output is recorded in
`Saved/BuildEditor/build-20261002-144539.log`. The editor was already closed
when the build started and was not reopened. In-game behavior has not been
tested after the repair.

## Captured runtime identity

After the user held the failing frame, the read-only bridge captured the live
PIE player `FPSGAMECharacter_0` in `UEDPIE_0_DayNight_Lighting`:

- `AKMViewmodel`: `SK_M4_FoldingSights_HK416`, visible=false.
- `StaticMeshComponent_0`: `SM_M4_RearSight`, visible=true,
  hidden_in_game=false, parent=`AKMViewmodel`, socket=`WPN_root`.
- `StaticMeshComponent_1`: `SM_M4_FrontSight`, visible=true,
  hidden_in_game=false, parent=`AKMViewmodel`, socket=`WPN_root`.
- `RuneSwordViewmodel`: `SK_FrostSword_Arms`, visible=true, attached to the
  separate `RuneSwordJumpPresentation` component.

The remaining parts therefore belong to the player's retained M4 viewmodel,
not a pickup or studio actor. The state is preserved in
`runtime_sights_captured.json`. Reading the state did not change any component
or weapon, stop PIE, or launch another application.

## Source lifecycle gap before repair

`M4FoldingSights.cpp` creates independent sight components with their default
visible state, without copying the current visibility of `AKMViewmodel`.
`UpdateFoldingSights` then updates their transforms but never synchronizes
visibility. `BeginPlay` unconditionally initializes weapon visuals, whereas
`TryAttachLocalProfile` does not apply an already attached profile again.
Consequently, initializing the default M4 after a profile has hidden its gun
rig can create visible sights under that hidden rig. This is a source-supported
explanation for the captured state; the precise initialization call order was
not traced in the user's running session.

The live capture establishes the exact owner and meshes. This diagnosis did
not modify gameplay source, weapon assets, or the running scene.

## Earlier static investigation

The supplied screenshot's circular aperture, cylindrical body and vertical
knurling match the existing M4 rear-sight source preview exactly:
`SourceAssets/M4FoldingSights20260909/rear.png`.
The sight mesh is `/Game/Weapons/M4FoldingSights/SM_M4_RearSight`; its pair is
`SM_M4_FrontSight`. M16's factory sights belong to its weapon skeletal mesh.
The user reported M16 A2 as their secondary gun before noticing the residue.
That equipment history does not establish the owner of the M4 components.

Current `M4FoldingSights.cpp` creates independent heads for M4, QBZ191, A762
and LMG201. Switching to another firearm destroys/rebuilds the heads; switching
to melee retains the old gun rig and its heads. `FPSGAMECharacterProfile.cpp`
currently recursively hides that rig after attachment setters. The folding
tick only updates transforms and does not re-show them. The source therefore
does not yet explain residual M4 heads surviving a complete M16 initialization.

The existing editor session loaded `UnrealEditor-FPSGAME.dll` after the prior
profile visibility change had been compiled. The user exited each observed
PIE session before the read-only component capture could inspect it. Both
captures returned no game world. Consequently the actual remaining actor,
parent and visibility state have not yet been captured; no lifecycle repair
is claimed from static identity alone.

`read_runtime_sights.py` reads current PIE worlds, affected character rigs and
any actor holding the exact independent M4 meshes. It captures owner, parent,
socket, mesh and visibility without changing the game, switching equipment,
ending PIE or launching an application. The user has been asked to keep an
existing residual frame running so this final ownership question can be read.

No gameplay source/assets were changed and no test was launched for this
diagnosis. Existing source previews and the user's screenshot were inspected.
