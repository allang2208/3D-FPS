# Infected miner: original EBS tool animation

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
