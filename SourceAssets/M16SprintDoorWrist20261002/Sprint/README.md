# M16 complete M4 sprint left-chain copy

This is animation-only production for Base, Drum, Angled, Vertical, Canted and
Prism. Each family has Enter / Loop / Exit, keeping the current M16 right arm,
rifle and mechanical source trajectories and the existing 0.3 / 0.6 / 0.3 s
timing. The complete saved M4 left chain replaces the old M16 sprint chain.

The prior M16 author called `shift_arm` even when its support shift was zero;
that routine re-solved the main arm and reset every twist helper to its parent
times the local rest transform. This copy never calls that solver. Donor
clavicle, upper/lower arm, wrist, auxiliary twists and fingers are transferred
together. Base uses the existing support contact translation as a rigid whole
chain move. Attachment handoff uses the existing registered whole-chain grip,
blended in local bone space. Loop uses the saved M4 chain directly.

The M16 native mesh wrist reference differs from M4. The corresponding common
runtime wrist correction is owned by the parent task. This source production
does not independently design a wrist correction or modify native mesh bind,
weights, scale, material, right fingers, USkeleton or the neutral 19-digit mesh
bindings saved by `M16Repair20261002/NeutralBind`.

`author_sprint_copy.py` runs in background Blender and actually saves six
editable Blend files and eighteen animation-only FBX files. `authored.json`
records sources, hashes, clip assets, donor actions and completion. No UE import
is performed by the author.

`import_sprint_only.py` is prepared for the existing mutex-protected UE batch
bridge or a background PythonScript commandlet. It imports those eighteen clips
to their existing registered paths, then calls `BakeClip` only for the three
sprint roles in each of the five existing M16 grip profiles. Other entries,
Family and profile metadata are retained. Package backups go into
`BeforePackages`, and the incremental `import-receipt.json` records actual saves.
Do not run the old whole-weapon M16 imports or the global profile installer.

No game, animation preview, render, screenshot or acceptance test is started.
Authoring completion and actual UE import/save completion are separate receipts.
