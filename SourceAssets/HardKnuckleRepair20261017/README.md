# Hardknuckle repair 2026-10-17

Production recipe: `ue_hardknuckle_gloves`, all 25 native bindings plus pickup.

`read_sources.py` exports actual runtime wrist geometry through UE. `author.py` restores the original glove and authors closed cuffs per native skin. `native_transport.py` retains only the prior binding transport. `review_geometry.py` is the scoped investigation, not a routine global test. `import_assets.py` saves all assets with resumable receipts. `publish_sources.py` updates the established production source files after save. The production `fix_glove_cuff.py` delegates to this authoring path.

The UE source face order is clockwise relative to its stored outward normals. Never reverse all triangles according to a right-hand-space visualization. Apply a handedness reflection when entering Blender.

Original body geometry is retained. No game or PIE was launched. Runtime acceptance remains with the user.
