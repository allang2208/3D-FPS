# AKM UE5 migration candidate

This folder is the isolated first-person AKM migration candidate for `FPSGAME`.
It does not overwrite the Godot source asset.

## Provenance

- Editable source: `E:/3d/akm-classic-staging/akm-classic-unified.blend`
- Godot reference export: `E:/3d/3-dfps/assets/models/akm_classic/akm_refined_v2.glb`
- UE destination: `/Game/Weapons/AKM`
- No new third-party model or animation was introduced by this conversion.

## Delivered assets

- `SK_AKM_Viewmodel_Source.blend`: editable, combined arms + weapon rig.
- `SK_AKM_Viewmodel.fbx`: skeletal mesh import source.
- `A_AKM_*.fbx`: idle, aim, fire, aim-fire, reload, empty reload, draw,
  holster, and inspect clips at 24 fps.
- `akm_reload_empty_candidate.png`: rendered empty-reload pose preview.

The weapon bones are prefixed with `WPN_`. The UE skeleton has one explicit
`VM_Root`, and preserves the muzzle, eject and magazine attachment bones.
The export report does not contain RearSight/FrontSight bones. Current ADS
uses a source-probed fixed transform; dynamic sight alignment remains pending.

## Validation

- `akm_source_action_validation.json`: source pose bounds.
- `akm_bake_validation.json`: finite combined-rig pose bounds.
- `akm_vertex_match_validation.json`: evaluated source/candidate vertex match.
  Across sampled frames in all nine clips, global maximum deviation is about
  `0.00000157 m` and RMS deviation is about `0.00000039 m`.
- `akm_unreal_import_report.json`: imported UE assets.
- `akm_unreal_pose_report.json`: sampled UE bone transforms.

The UE import keeps 24 fps and all original clip durations. The C++ gameplay
integration currently drives draw, hip/ADS fire, normal/empty reload, inspect,
ADS FOV/offset, hitscan damage, and magazine/reserve ammunition.

## Publication boundary (2026-09-09)

This is a partial migration, not complete behavioral parity. Equip currently
starts reload_empty at 1.57 s rather than generating Godot's 0.18 s idle blend
followed by source time 1.75 s. Camera noise uses UE Perlin, fire uses hitscan,
and dynamic sight anchoring and some recoil-load multipliers remain pending.
The automated audit captures states but does not assert parity or test physical input.
Superseded debug captures and the blend1 backup are recoverably archived in
../../trash/akm-migration-20260909/manifest.json. Editable blend/FBX and final
previews are retained locally; redistribution licenses have not been fully audited.
