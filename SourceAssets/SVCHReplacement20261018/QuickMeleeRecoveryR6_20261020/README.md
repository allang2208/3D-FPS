# SVCH R6 recovery subframes

Preserve the R5 authored motion. Fix only how right-arm recovery is represented
as a delta over the shared SVD compressed animation. Original 120 Hz keyframes
missed a large source excursion at frame 67.5; integer-frame acceptance was
insufficient.

Order: read compressed inputs -> `author_subframes.py` -> `check_dense.py` ->
guarded `install_profiles.py` -> repeat the held-out check using `SavedReadback`
and the existing native graph capture for anchor preservation.

Do not use `check_subframes.py`'s optional interpolated-input fallback as engine
proof. The actual exported COMPRESSED inputs are authoritative. Likewise, the
native capture's integer samples do not replace the held-out subframe check.

Only 27 right-arm tracks within frames 54..90 receive additional samples;
the highest density is confined to frames 66..70. Left arm, weapon, V9 and all
other actions remain unchanged. The editable motion remains the R5 Blend;
there is no new motion or runtime solver.

`Review` contains offline reconstructions, not gameplay screenshots. Interactive
visual acceptance remains pending.
