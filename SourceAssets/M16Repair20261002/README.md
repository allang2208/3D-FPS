# M16 switch visibility and left-hand surface repair

The user rejected this first position-only hand repair after testing spell
release and reloads. It is retained below as production history. The replacement
production is documented in `NeutralBind/README.md`: it changes the actual left
digit mesh reference binding and rebuilds the matching common V7 geometry.

On 2026-10-03 the eight rejected scripts, first authoring manifest and editable
outputs were moved to `trash/weapon-arms-publication-20261003/SourceAssets/M16Repair20261002/`.
The exact paths and hashes are in `SourceAssets/WeaponArmsPublication20261003/archive-manifest.json`.
The history below describes those archived files; do not run the old installer.
The eight `Authored/*.position_patch.json` files, `Input`, `Before/Packages` and
`installed.json` remain here: NeutralBind reads the prior installed positions
and package hashes before replacing the reference binding. They are current
remaking dependencies, rather than unused rejected outputs.

The current M16 weapon embeds the accepted V7 surface in native material slots
13 and 14. The saved weapon, BarePalmV7 companion and WristCoverage skin have
identical arm positions, weights and reference bones after vertex reindexing.
There is no separate M16 factory sight component; the carry-handle sight and
front post are part of the weapon geometry. The current outfit meshes contain
no weapon-bound vertices.

`FPSGAMECharacterProfile.cpp` now propagates visibility **off** after attachment
setters finish when the rifle is stowed. Showing a rifle still leaves individual
attachment visibility to the setters. The editor and game objects, editor DLL
and game executable produced by the existing background builds include this
source revision; their timestamps and hashes are recorded in
`native-build-receipt.json`.

The M16 reference pose curls the hand. The original common-to-native transfer
linearly blended bone transforms, compressing portions of the left finger bases
and webs. `hand_binding.py` changes this left digit/palm transfer to dual
quaternion blending, feathered into the palm. It keeps the common V7 source,
native reference skeleton, weights, topology, canonical UV coordinates, weapon
materials and animation assets. The position-only repair is also authored on
the current black leather, tactical, steel and fingerless glove surfaces, plus
the worn skin companions, so they retain matching skin/glove shape.

Production sources:

- `Authored/authoring.json`: eight asset patches and their exact input hashes.
- `Authored/M16_BareArmsV7_Editable.json`: editable mesh with corrected positions
  and affected corner normals.
- `Editable/M16_BareArmsLeftHandBind20261002.blend`: native M16 reference rig and
  editable hand geometry, produced with background Blender.
- `install_left_hand.py`: writes the existing registered UE assets, keeps
  material slots, refreshes affected normals/tangents and generates their LODs.
- `Before/Packages`: original packages captured before editing each asset.
- `installed.json`: written incrementally **only after each UE asset is saved**.

Production commands are the background authoring script, the background Blender
source export and the existing mutex-protected UE Python bridge. Do not replay
the historic M16 whole-weapon or reload imports: those would overwrite later
weapon materials or accepted reload work.

The import stops if the game is running, a target has unsaved changes or an
input package changed after authoring. It does not end play or close an editor.
After the user ended play, all eight registered UE assets were saved through
the existing mutex-protected bridge. `installed.json` contains each original
package backup, before/after hashes and the recorded save status. The matching
bridge result records `CLOVEN_M16_HAND_INSTALL_COMPLETE 8` with success true.

No game, render, screenshot, regression or acceptance run was started. The
weapon switch behavior and hand appearance remain for the user to test.
