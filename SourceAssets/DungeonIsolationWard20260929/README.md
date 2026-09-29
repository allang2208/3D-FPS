# Abandoned Isolation Ward — production special combat room

Current module `AbandonedIsolationWard` is registered in `/Game/GameMaps/L_Dungeon_Randomized`. The 60 × 9 m main hall has its only dungeon ports at UE X = -3300/+3300 cm. The former outside entrance is sealed; the decontamination room remains accessible from the hall. Selection is 30% eligibility per run, at most one on Approach, subject to legal placement. Its sealed encounter uses 6–8 elite enemies and the existing iron gates.

The saved module includes independently opening/breakable glass leaves and observation panes, 1.5× beds with fitted collision, sparse carts and noncolliding IV stands sharing placement occupancy, 13 fixed benches, scanned floor/wall blood, fault lights and constrained random posters/room numbers. Floor blood width is 87.5–212.5 cm (2.5×); wall blood remains 35–85 cm. Counts are targets, not guarantees when a site cannot fit.

The user finished the temporary scene test and requested its removal. Both standalone map routes are retired, along with the temporary menu, MapsToCook, return logic and dedicated test Actor. Production components and assets remain. Do not run old standalone installers from archives.

## Active authoring and import chain

- `Scripts/prepare_design.py`, `pool_design.py`, `room_blood_design.py`: architecture and production configuration; one full room, no size variants.
- `Scripts/author_ward.py`: approved corridor surfaces and architecture. Full source `Authored/AbandonedIsolationWard_Subject.blend` retains its historical filename; the filename does not imply a live sample map. Partial geometric corrections may still use `WardWindowRevealFixV8.blend`.
- `Scripts/author_glass_doors.py` → `author_breakable_glass.py` → `import_assets.py`: fitted door/frame/panes and original fractured meshes; `author_glass_fracture_material.py` plus `GlassFragmentsV5.hlsl` author the cosmetic burst.
- `BedScatter/Scripts/author_bed_collision.py` → `import_bed.py`: current bed derivative and fitted collision, without loading a sample map. This asset-only import entry was extracted during cleanup; it was not executed this turn because the production bed is already saved.
- `MedicalProps20260929/author_props.py`, `import_assets.py`, `prop_design.py`: the cart/IV derivatives and sparse scatter recipe. `BenchLayout20260929/Scripts/bench_design.py` maintains the fixed bench layout.
- `Scripts/author_atmosphere_materials.py`, `author_scanned_blood.py`: glass/fault lights and user-owned Quixel scan materials. The old procedural V3–V5 blood authors are retired.
- `WallArt/Scripts/read_sources.py`, `read_mesh_layout.py`, `author_layout.py`: source metadata extraction and safe hanging rectangles. Source geometry/export payloads remain local.
- `Scripts/build_pool_module.py`, `extend_catalog.py`, `install_pool.py`: assemble current runtime actors/parts and incrementally save generator dependencies. `WallArt/Scripts/install.py` performs a wall-art-only catalog update.

Native implementation: `WardRoomAssembly`, `WardBedScatter`, `DungeonBloodScatter`, `WardBreakableGlass`, `DungeonWallArt`. Deferred actors are populated after structural collision exists, owned by the generator and removed with the room. `Config/module.json` is the production module; module-draft retains historical author metadata and points to production.

## Local assets and history

Editable meshes, manifests/pose bounds, texture sources, UE packages and import receipts are required local restoration inputs. Published scripts are not a downloadable, fully licensed scene. See [asset notices](../../ThirdPartyNotices/ISOLATION_WARD_ASSETS.md) and [publication boundary](../../Docs/Gameplay/dungeon-rooms-publication-20260929.md).

Current [pool record](../../Docs/Gameplay/dungeon-isolation-ward-pool-20260929.md) and [wall art](../../Docs/Gameplay/dungeon-ward-wall-art-20260929.md). Older V2–V8 documents retain their dated making history. Their `Before`/`SourceBackup` snapshots and retired map installers now reside at `trash/dungeon-rooms-closeout-20260929/<original path>`; the temporary-test archive remains separate. No gameplay/visual tests or editor restart were performed during cleanup.

Archive status update: the user cleared trash during closeout and explicitly requested continuation. Earlier sample maps/installers/backups were deleted by the user after archival; their paths above are historical, not available recovery locations. Only the second closeout asset batch remains in trash; consult the publication archive manifest. Current production assets/author inputs remain in place.
