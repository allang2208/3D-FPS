# AKM integration, 2026-09-10

Latest equip revision: [EquipCharge](EquipCharge/README.md) keeps the magazine seated and the left hand in idle grip, plays only the source right-hand charging action, and uses a 1.7 s equip clip with matching pull/release audio.

Latest wood revision: [WalnutFab](WalnutFab/README.md) uses the selected Fab Quixel Walnut Veneer 4K scan, longitudinal wood UVs for stock/handguard, restrained surface relief and a red-brown satin finish. Runtime now loads `/Game/Weapons/AKMIntegration/WalnutFab/SK_AKM_MannyNative` with the existing SourceMatched animations. This supersedes the ambientCG redwood described in the historical sections below.

Status: SourceMatched animations and Fab Quixel metal are now integrated. The M4 mesh-specific metal atlases were rejected because their UV layout does not match AKM. The user's current requirement is Fab material assets; the already-acquired Fab Quixel Dirty Metal scan drives an AKM-only dark steel material. Existing redwood and M4 hand materials remain.

## Latest source-matched revision

Runtime mesh and animations now load from `/Game/Weapons/AKMIntegration/SourceMatched`. `build_source_matched.py` corrects anatomical palm orientation and MCP alignment and transfers the original AKM finger motion instead of freezing the M4 idle hand. Native M4 mesh geometry, weights, rest translations and clip durations are retained. See `SourceMatched/README.md` for method and provenance.

`SourceMatched/AKM_Fab_SourceMatched_Editable.blend` contains the animated source and packed Fab metal/redwood maps. `SourceMatched/Delivery/AKM_native_candidate.mp4` contains actual runtime footage with mixer audio. Source and engine renders were inspected at idle, retrieval, insertion and bolt operation. This is adaptation to a different hand mesh, not a claim of identical source topology or zero contact error on every vertex.

Validation: `SourceMatched/import.json` confirms all ten imported clip durations. `SourceMatched/fab_material.json` confirms the new metal bindings and unchanged hand/wood slots. Editor build `build-source-matched-final.log` passed, suffix 2026091522. `runtime-akm-source-matched-fab-v1.log` passed firing, ADS, both reloads, switching, warehouse and profile reload with zero failures and clean exit. `runtime-akm-source-matched-switch-v3.log` passed repeated modified-M4/AKM switching using a clone of the saved regression fixture, including body and sight visibility.

The first existing-profile test lacked a copied fixture. The second copied the current player save: AKM geometry passed, but cycling failed because this snapshot did not have the required second equipped weapon. The third explicitly cloned the preserved `visibility_1514` fixture. None of these audits modified the formal player save. Imports exit 1 due to existing unrelated commandlet errors; the specific import/material PASS markers and saved asset reports are the success evidence.

## Modified M4 to AKM visibility repair

The user's saved M4 has a suppressor and large drum. Its hidden material-section indices survived a same-LOD-count skeletal mesh swap, hiding AKM's receiver/barrel and sight sections. The original factory-M4 fixture did not cover this case. `akm-existing-1513/frame_0030.png` reproduces the missing gun geometry from an isolated copy of the actual player save.

`InitializeWeaponVisuals` now restores all section visibility immediately after selecting the new mesh, before the current weapon's attachments are reapplied. `-AKMExistingProfile` adds normal backpack equip and repeated modified-M4/AKM switching to the audit, with explicit receiver/sight section checks. The previously absent `Icons/ue_akm.png` was separately filled with the actual runtime model render.

Verified with `runtime-akm-visibility-fixed.log`: normal backpack equip, AKM receiver/sights visible, modified M4 attachments restored, repeated switch back to AKM, zero failures. `Saved/AKMIntegrationAudit/akm-visibility-fixed/frame_0030.png` shows the complete gun after the repair. Editor build suffix 2026091514 passed; an already-open editor must restart to load the fix. The formal player save was not changed during these reproduction runs.

## Earlier M4-atlas material revision (superseded)

Runtime mesh: `/Game/Weapons/AKMIntegration/Materials/SK_AKM_MannyNative`. Metal slots reference the actual M4 `Body_001` and `Flash_Hider_001` instances. The wood slot uses editable `M_AKM_Redwood` with ambientCG Wood051 2K maps, deep red tint, subtle normal and satin roughness. Both Manny hand material slots remain the M4 defaults. See `Redwood/README.md` and `Redwood/applied.json` for source, CC0 license, hashes and parameters. Fab's Quixel download could not be retrieved as a local file; the used maps are an explicitly documented direct-source replacement.

`runtime-akm-redwood-v2.log` passed the game input chain with zero failures and a clean process exit. The earlier gray default-material issue was fixed by enabling skeletal-mesh usage. New runtime frames show the applied redwood finish. `Redwood/Delivery/AKM_native_candidate.mp4` contains the actual runtime footage and mixer audio; `Redwood/AKM_Redwood_Editable.blend` preserves the editable native baseline with packed wood maps. The engine material graph and import scripts reproduce the authoritative runtime finish.

## Identified gun source

- Author: Ag72, Fab listing https://www.fab.com/listings/54921e31-5077-4ad8-9d5a-7b8bdd6ac7d3
- The signed-in listing showed the item already in the user's library and CC BY 4.0.
- Downloaded FBX SHA-256: `BBB7A8CF56D7ED7EF850B410933C056BB9C478F229A7576D5C585B7102D57D43`, 935148 bytes.
- This exactly matches `../AKMReplacement/UserProvided_AKM.fbx`.
- Fab's download dialog lists `akm.fbx`, `source.zip` (OBJ), and converted glTF/GLB/USDZ. No separate texture RAR was listed. The browser reported the OBJ download complete, but no usable local ZIP was obtained; its contents have NOT been verified.
- The matching TurboSquid listing https://www.turbosquid.com/3d-models/akm-assault-rifle-3d-model-2475271 explicitly lists `AKM.fbm.rar`, costs USD 2, and displays editorial-use restrictions. No purchase was made. This listing is evidence for the missing file name, not authorization to use that package in the game.

## Shared hands

`Native/AKM_MannyNative_Editable.blend` keeps the current M4's `SK_Manny_Arms_Export` mesh, native skeleton, vertex weights, and materials. The gun and ten AKM actions are adapted to that skeleton. `build_native_arms.py` and `import_native.py` reproduce the candidate. `Native/retarget.json` records source durations and IK reach errors. `Native/import.json` records imported clip durations.

The earlier `SK_AKM_SharedArms` candidate remapped the Manny mesh into the legacy AKM rest pose and visibly stretched the palm. It is superseded by the native-skeleton candidate and is not an accepted final asset.

`NativeBaseline/` reproduces the first native-skeleton baseline using `build_native_arms.py -- --baseline`; `import_verified_baseline.py` imports that baseline into the runtime `/Game/Weapons/AKMIntegration/Native` directory. The later contact experiments remain isolated in source `Native/` and must not be published as accepted animations. `Native/contact_probe.json` found intersections during approach, release and bolt transitions, even though the fully held magazine phase was corrected. Further contact authoring is required.

The tested baseline preview is `Native/Delivery/AKM_native_candidate.mp4`, recorded from the `akm-native-v2` run with actual mixer output and wall-clock screenshot timing. Static external renders in `Native/idle.png`, `reload.png`, and `reload_empty.png` reflect later contact experiments, not an accepted final version. All still show replacement gun materials.

## Gameplay

Native item `ue_akm` uses 7.62 ammo, a 30-round magazine, and AKM-specific stats. Selection, workshop overview, warehouse grant/transfer and profile persistence are connected. `AKMIntegrationAudit.cpp` and `run.ps1` exercise an isolated profile. `runtime-akm-native-v2.log` passed the native-skeleton gameplay chain. `runtime-akm-native-v2-readback.log` independently restored the AKM instance with 17 rounds and completed with zero failures. These checks do not certify final contact poses or original materials.

The earlier readback process hung after requesting exit, including with audio disabled, and the owned process was stopped. The audit now avoids requesting screenshots during readback/exit. The prior unrelated whole-project compilation blocker was subsequently resolved, and the current Editor build passed (`material-build-editor.log`, module suffix 2026091428). No unrelated enhancement code was changed by this material task.

The fixed cross-process readback was then rerun successfully: `runtime-akm-redwood-v2-readback.log` restored the saved AKM and completed with zero failures and a clean process exit.

`baseline-import-console.log` and `NativeBaseline/import.json` record the successful final baseline asset import after terminating the already-exiting owned readback process that held the mesh file open.
