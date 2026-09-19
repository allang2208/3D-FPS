# AKM redwood finish

User-approved direction: reuse current M4 metal materials and tint a free wood texture redwood. This replaces the request to obtain Ag72's original texture RAR.

Downloaded and used: ambientCG Wood051, 2K JPG, https://ambientcg.com/view?id=Wood051 . License: CC0, https://docs.ambientcg.com/license/ . The Fab Walnut Veneer browser download did not produce an accessible local archive, so this is an explicitly identified direct-source substitute, not Quixel Walnut Veneer or the original AKM author's texture package.

The ShareTextures American Walnut download is NOT used: its current custom terms differ from unrestricted CC0. Its archive remains isolated in this source folder, outside Content.

Run `../apply_m4_metal.py` then `../apply_redwood.py` with Unreal's Python commandlet to reproduce the engine materials. `applied.json` records archive SHA-256, texture origin, material parameters and exact runtime bindings. The wood has adjustable `RedwoodTint`, subtle normals and satin roughness. M4 metal instances and both Manny hand materials are reused by reference; the original M4 assets are not edited.

The engine material graph is editable. `make_editable_source.py` creates a Blender copy of the native baseline with the same wood maps and finish; engine M4 material bindings remain authoritative for metal appearance.
