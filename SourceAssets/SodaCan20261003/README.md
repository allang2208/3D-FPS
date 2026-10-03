# Soda Can — 2026-10-03

The real Dkalq Studio Soda Can came from the user's downloaded Fab cache:
`D:/FPS3D/VaultCache/FabLibrary/Soda_Can-685c71b6/fbx`.
Listing: https://www.fab.com/listings/685c71b6-e33d-4262-9149-0a01787e0d85
The original source and cache metadata stay in place. The fictional SWESH
packaging, original UVs, and Color/Roughness/Metalness textures are retained.

`author_soda.py` produces the bottom-origin, +Z upright static mesh at a height
of 12.2 cm. Original proportions and topology are retained. The editable
`SodaCan_Authored.blend`, centimeter FBX, and `manifest.json` are saved here.
`render_icon.py` separately authors the 320×320 transparent inventory PNG,
with an orthographic view and 91% silhouette fill. It uses the same PBR maps.
It does not re-export the mesh.

`import_soda.py` saves the actual static mesh, metallic PBR material, and three
textures under `/Game/Items/Consumables/SodaCan20261003`. `save_assets.ps1`
waits for existing UE/build processes and invokes only a headless import
commandlet. No editor UI, gameplay, automated tests, or QA captures are started.
`import_receipt.json` records completed asset saves.

`configure_soda.py` publishes `soda_can` as a 1×1, single-use consumable with
hydration +20, SAN +10, and a total use animation of 2 seconds. The existing
backpack/compartment right-click and quickbar routes start that same animation.
The left hand grips the middle of the can; it tilts toward the mouth and retracts
naturally. Random water-swallow sounds use the existing drinking audio pool.
Both effects settle at contact in the existing inventory transaction.

The revised, tighter V7 can grasp is authored independently in
`SourceAssets/SodaCanGrip20261003/grip_profile.json`; the catalog producer reads
that profile. The palm seats against the can body, the four fingers wrap it,
and the thumb opposes them. The hand retains its grip until the visible can
releases at 1.94 seconds, instead of blending back to the equipment pose early.

The same catalog update gives small bread hydration −10 and baguette hydration
−30, preserving hunger +15 / +60. Their current motion timing is authored in
`SourceAssets/FoodGrip20261003/natural_food_motion.py`.
Existing animated-consumable instance migration refreshes these catalog fields
when old profiles load, while preserving identity, placement, and remaining uses.

Runtime behavior and final hand contact are left for the user's game test.
