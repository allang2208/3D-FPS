# Infected miner: single-hand pickaxe composite

Current: [natural wrist and forearm correction](../../Docs/InfectedMinerNaturalWrist20260913.md). Run Blender `relax_wrist_chain.py`, then UE Python `import_natural_wrist.py`. It replaces the three clips in the original miner BP with `NaturalWrist20260913` animations and reuses the enlarged `DragGround` mesh, bind, grip and materials. Editable/export files are under `SourceAssets/InfectedMiner20260913/NaturalWrist/Delivery`. Requested previews use `--natural-wrist`, optionally `--state Walk`. No native rebuild or gameplay test was performed for this revision.

Latest: [enlarged pickaxe, trailing carry and ground slam](../../Docs/InfectedMinerDragGround20260913.md). Run Blender `author_drag_ground.py`, build the editor module, then run UE Python `import_drag_ground.py`. This extends the accepted single-hand version without changing its bind or skin. Current assets use `DragGround20260913`, and local editable/export files are under `SourceAssets/InfectedMiner20260913/DragGround/Delivery`. Requested preview scripts use `--drag-ground`, optionally `--state Walk`.

The following workflow produces the earlier accepted single-hand version and remains its source history.

Current route: [single-hand pickaxe correction](../../Docs/InfectedMinerPickaxe20260913.md). Run `rebuild_pickaxe_tools.py` in UE Python, then Blender `package_default_tools_blend.py -- --pickaxe`. Requested previews use Blender `render_default_preview.py -- --pickaxe` and Python `package_default_preview.py --pickaxe`. Outputs are in `SourceAssets/InfectedMiner20260913/PickaxeSingleHand/`; UE assets are in `/Game/Monsters/InfectedMiner/PickaxeSingleHand20260913/`.

This uses the actual EBS PickAxe body/legs/left arm, existing relaxed right arm and accepted fingers, uniformly sped up to 1.8 seconds. It is a composite from a two-hand source, not native one-hand mocap. `AnimPoseExtensions` plus the existing editor animation controller bake the layer without adding a new C++ asset API. The existing miner BP and its contact window are updated. Body/hand geometry, rest skeleton, skin and materials are retained.

After packaging the blend, run Blender `orient_pickaxe_head.py` and UE Python `import_pickaxe_head.py`. These rotate only the rigid pick head by 90 degrees around its shaft so the tips follow the swing plane, then import `SK_InfectedMiner_Pickaxe` using the accepted skeleton/materials/physics. The shaft, grip and animation remain unchanged. Run the final requested preview after this step.

The axe route below was rejected because its motion source was wrong. Keep it as history; do not run `rebuild_default_tools.py` over the current miner.

Current route: [2026-09-13 delivery notes](../../Docs/InfectedMiner20260913.md). Work in `D:/FPS3D/FPSGAME`, UE 5.8.2 and Blender 5.1. The user rejected CMU, KayKit and the earlier procedural strikes. Do not run those routes over the current delivery.

## Rebuild

1. `export_default_tools.py` in UE Python exports the original Easy Building System V10 mannequin and tool clips. Mesh export requires `-AllowCommandletRendering -RenderOffscreen`; it does not render acceptance images.
2. Build `FPSGAMEEditor Win64 Development` after native changes. The `InfectedMiner.ApplyAcceptedGrip` asset operation copies only the accepted finger pose from the existing idle clip. Never roll back `UnrealEditor.modules` over another task's newer module.
3. Run `rebuild_default_tools.py` in UE Python with `-NullRHI -unattended -nosound`. It uses UE's native IK Retargeter, exact chain mapping, automatic target pose alignment and the original tool clips. It saves the new retarget assets, freezes accepted finger tracks, exports animation-only FBX, and binds the new idle/walk/attack and contact window to the existing miner BP.
4. Run Blender `-b -t 4 --python Tools/InfectedMiner/package_default_tools_blend.py`. This replaces action data in a copy of the accepted editable model, preserving the original mesh, weights, bind and materials. No rendering or tests.

Outputs: `SourceAssets/InfectedMiner20260913/Delivery`; UE assets: `/Game/Monsters/InfectedMiner/EBSDefault20260913/`. The unchanged body/hand model and materials remain in `AuthoredChopFinal` despite that historical folder name. The existing pickaxe remains until a replacement Fab model is obtained.

## User testing

`Open-MinerVillage.cmd` opens the existing village. Restart an already-open editor/game to load the updated module and asset references. The existing village spawner uses the same miner BP, so no duplicate spawn or map rewrite is needed.

Tests, audits, screenshots and preview renders run only when explicitly requested. Historical CMU/KayKit reports do not establish the result of this new version.

## Historical tools

`fetch_realistic_mocap.py`, `retarget_cmu_strike.py`, `import_mocap_strike.py`, `finalize_mocap_delivery.py`, `write_manifest.py` and `write_delivery_docs.py` belong to the rejected CMU delivery. They are retained for provenance, not current rebuild entrypoints.

The earlier `author_attack.py`, `author_power_strike.py`, `refine_grip.py`, `retarget_authored_chop.py`, `restore_previous_attack.py`, `restore_attack_in_ue.py` and `import_power_strike.py` also belong to superseded stages. The accepted hand snapshot contains an old V03 attack and must not be restored wholesale.

Fab/Epic originals, derived binary assets, donor files and previews remain local. Publish only the exact owned code, source metadata and documentation paths.
