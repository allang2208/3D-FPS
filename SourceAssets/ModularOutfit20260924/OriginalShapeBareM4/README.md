# Original-shape M4 bare hands

Current M4 candidate: `SmoothSkinV2`, with constrained surface fairing, rebuilt
hand normals and height-derived pore detail. V1 below is retained as authoring
history. See `Docs/Characters/original-shape-bare-m4-smooth-v2-20260924.md`.

This derivative retains the accepted native M4 hand geometry and skin binding.
It supersedes `RealisticM4Candidate` only in the M4 `bare_arms_candidate` profile.
The original tactical glove asset and restoration equipment remain intact.

Editable source: `M4_OriginalShape_BareHands_Editable.blend`. The original basis,
local dorsal shape key (maximum 0.6 mm), grip/seam lock authoring group, original
rig and packed skin maps are retained. Native weights are inherited directly by
the UE asset; the authoring group is not exported as a deform bone.

`M4_original.json` is the original native input. `M4_bare_shape.json` contains the
authored positions, material partition and anatomical texture coordinates.
`saved.json` is the actual UE save receipt, not a runtime validation result.

Production and scope: `Docs/Characters/original-shape-bare-m4-20260924.md`.
No PIE, animation playback, preview rendering or automated acceptance was run.
