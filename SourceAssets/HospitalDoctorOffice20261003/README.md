# Hospital doctor office and ward details, 2026-10-03

Requested scope: explain and refine the bedside equipment strip and wall rails;
repair the disappearing body of generated patient boxes; furnish the empty room
at the hospital corridor's east end as a doctor's office.

The wide strip was an unfinished bedside utility panel. The separate lower strip
was wall protection. The new original geometry has attached round handrails,
return ends and regular screwed brackets. Bedside panels now seat against the
wall, with power sockets, equipment ports and call buttons attached to the panel.

The office occupies the existing room (UE local X 1714–2986, Y 464–1036 cm).
It reuses staff desks, chairs, waiting bench and table. Two bookcases and a shelf
with a working drawer are searchable scene containers, with separate storage IDs.
Documents and binders provide desk details. Entry and furniture clearances are
part of the authored layout. The old DECON sign is replaced with DOCTOR OFFICE.

WardBedScatter and WardRoomAssembly assign component mobility before a runtime
body mesh, because UE rejects SetStaticMesh on static components after BeginPlay.
Generated patient boxes use wall bays and the existing shared occupancy ledger,
including the full lid sweep. Blocked bays are omitted rather than forced.

Authoring order:

1. Run author_ward_details.py and author_desk_props.py with Blender in background.
2. Run prepare_office.py with Python.
3. Run build_native.ps1 for normal Editor and Game binary builds.
4. Import meshes with install_background.ps1 -Phase assets when no editor holds
   the project, or import_existing_editor.py through the shared MCP bridge.
5. Save maps with install_background.ps1 -Phase scenes, or the existing-editor
   wrapper through the bridge. The production catalog and saved hospital preview
   are merged in place; unrelated modules and map edits are preserved.

Actual completion is recorded by Receipts/native-build.json, assets.json and
install.json. Script preparation alone does not establish saved engine assets.
No game run, tests, screenshots or acceptance renders are requested or performed.

Preview: /Game/GameMaps/Design/L_Hospital_Theme_Subject
Production: /Game/GameMaps/L_Dungeon_Randomized
