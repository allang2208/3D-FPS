# M16 left finger neutral mesh binding

The user rejected the previous position-only DQ patch: the left fingers still
looked narrower than the common hand, especially during spell release and
reloads. The old patch is retained as production history and is superseded by
this repair.

The main M16 mesh has complete left digit geometry in both its source and
render data. Its only LOD contains 37,122 arm triangles and all five fingers'
skin weights. The current runtime path does not hide or zero-scale M16 digits.
The weapon contains the same common V7 topology as its V7 skin companions.

The original authoring pre-skinned the common neutral hand into M16's curled
mesh bind, using a blended linear transform. Subsequent GPU skinning during
open-hand actions applies another blend against that curled inverse bind.
The product of these blends is not the same as skinning the common surface
once; changing only the baked surface positions leaves this cause in place.

This production changes only the 19 left digit mesh reference rotations
(including the four metacarpals) to the common V7 neutral rotations. Native
local translations, scale, hierarchy, hand/wrist/forearm references, the right
hand, mechanical bones and shared M16 USkeleton are retained. Naked-hand
geometry is authored from the common V7 coordinates. Glove shells are recovered
from their pre-DQ source and re-bound with the same neutral references.

`SkeletonModifier` commits the per-mesh reference changes and rebuilds the
actual inverse reference matrices. This is a transform-only mesh change and
does not modify the shared animation skeleton. The installer then writes the
matching geometry and regenerates each companion's existing LODs, preserving
current material slots and existing animation assets.

The retained 50 M16 base/attachment animation assets all contain tracks for
the 19 changed left digit references, so their existing keyed native grips
continue to supply the animated poses. The spell component derives its finger
reference axes from the skeletal mesh reference pose; it will now use the
common neutral left hand when new gameplay components load these saved meshes.

Production entry points:

- `author_neutral_bind.py`: produces the binding and geometry patches.
- `Authored/authoring.json`: production manifest and source package hashes.
- `install_neutral_bind.py`: applies the production through the existing UE
  batch bridge or unattended commandlet.
- `Before/Packages`: package backups of the superseded DQ result.
- `installed.json`: written incrementally after each actual package save.

No editor/game is launched for acceptance, and no gameplay, animation preview,
render or regression test is performed. Final appearance is for user testing.

All eight registered meshes were saved through the existing running editor's
mutex-protected Python bridge. The completed bridge returned `success=True`
and `CLOVEN_M16_NEUTRAL_BIND_INSTALL_COMPLETE 8`. The incremental
`installed.json` records their package backups and saved hashes. This confirms
production/save completion; it is not runtime or visual acceptance.
