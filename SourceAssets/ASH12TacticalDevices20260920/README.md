# ASH-12 tactical accessories

- The user requested the existing laser and flashlight in a new ASH tactical slot.
- Donors: accepted `TacticalDevices20260913/M4/laser` and `TacticalDevices20260913/HunyuanV3/M4/flashlight`. Original donor generation/provenance remains in those folders. This task introduces no new downloaded or generated body.
- Host: ASH12 Surface20260919 editable source; mount sample receipt in `mount_geometry.json`.
- `author_vibe.py`: in-editor Vibe3D fit, replacement side saddle, black-metal dry/wet shader creation, sockets, FBX export and targeted package saves.
- Mesh local frame: centimetres, +X forward, +Y outward. Left-rail mount relative to ASH sight frame `(29.5,-3.19,-8.25)` cm; rotate local X by 180 degrees at the component, so the clamp faces the left rail. Geometry, UV and positive unit scale remain unchanged.
- UV0 and donor mesh normals retained. UV1 = ASH 4cm coating. Mount UV3 supports the existing ASH grip-metal shader.
- `save_editable.py`: package the exported meshes and body textures into individual editable Blender files; this does not render or test the models.
- Laser and light retain Emitter / AimGuide sockets, standard runtime occlusion, ADS convergence and visibility behavior.
- Reuse existing UI images `tactical_laser.png`, `tactical_flashlight.png` and `category_tactical.png` because these are the same accessory bodies. The fitted clamp is a host-specific interface.
- Initial integration did not run game tests. The subsequent user-requested position/scale diagnosis is recorded in `scale_before.json`, `bone_scale.json`, `left_rail_geometry.json`, and `left_mount_receipt.json`; no full gameplay regression was run.
- Repeated placement report: `render_rail_diagnosis.py` and `render_engine_assembly.py` render the actual source and engine-exported geometry. `read_engine_mount_frame.py` reads the imported skeleton frame. The ribbed two-screw side rail is below the small handguard vent row; the source and engine-exported placements agree. These are diagnostic Blender renders, not in-game captures.
- The left-placement Live Coding process crashed two seconds after patch success and was restarted with the old base DLL. The normal Editor build recorded in `Saved/BuildEditor/build-20260920-005117.log` has now persisted the change in the base module. Do not infer restart persistence from the earlier Live Coding success alone.
