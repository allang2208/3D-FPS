# M1911 shared attachments

Production sources for the M1911 holographic sight, panoramic red dot and suppressor.

See `Docs/Weapons/m1911-shared-attachments-timing-20260913.md` for runtime integration and timing changes.

Source provenance is retained in `sources.json`: these are local derivatives of the existing accepted game assets, with no new external download or changed license grant. The original shared assets and accepted M1911 skeleton/actions are preserved.

Production order:

1. UE Python `prepare_assets.py` exports the three shared source meshes and records current imported action lengths.
2. Blender `measure_weapon.py` reads the current Hero geometry and rig interfaces for authoring.
3. Blender `author_parts.py` creates fitted FBX variants; `bake_finish.py` bakes the current M1911 coating.
4. UE Python `import_assets.py` imports meshes/materials into `/Game/Weapons/M1911/Attachments20260913`.
5. Blender `assemble_editable.py` saves `M1911_FittedAttachments_Editable.blend` with the accepted rig and both optic alternatives.

`M1911_Attachments_Editable.blend` stores canonical attachment geometry; `M1911_Coating_Editable.blend` stores the authored coating graph and baking plane. PBR PNGs are under `Textures/`. No preview renders or gameplay tests were performed.

Runtime mounts are computed from the imported rest hierarchy rather than assuming that bone local axes equal the weapon axes. The sight frame is projected onto the root-up plane, the optic uses slide-relative mounting, and the suppressor uses barrel-relative mounting. The legacy muzzle marker is 0.598 cm below the refined barrel's bore center; the fitted suppressor applies that correction.
