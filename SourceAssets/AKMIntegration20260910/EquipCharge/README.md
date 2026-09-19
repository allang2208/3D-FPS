# AKM charge-only equip

User requested an attached magazine throughout equip, left hand already holding the weapon, and only the charging action. The original SourceMatched equip was rendered and inspected at source frames 0, 60 and 120. It contained magazine insertion before the right-hand bolt action.

`build.py` retains source frames 84–252 (120 Hz), adds 22-frame entry and 14-frame exit transitions, and fixes the magazine and left arm to their idle transforms relative to WPN_root. Final duration is 1.7 s. The source magazine bone is `WPN_SOCKET_Magazine`; world-space names inferred from the model must not be substituted. `report.json` verifies relative left-hand/magazine position drift below 0.000001 m. Right-hand motion and bolt travel remain source-driven.

`import.py` imports only `A_AKM_equip` to `/Game/Weapons/AKMIntegration/EquipCharge`. The runtime selects this clip for AKM; other animation paths remain unchanged. Equip audio uses only ChargePull at 0.55 s and ChargeRelease at 0.80 s, matching the measured bolt motion; the old combined EquipSound is suppressed for this clip.

`build-module.log` succeeded. `import.log` emitted AKM_EQUIP_CHARGE_IMPORT_PASS and imported duration 1.7 s. `runtime-akm-equip-charge-v1.log` logged the new asset on initial equip and repeated switches, completed with zero failures and clean exit. New source contact renders and actual runtime frames were inspected. `Delivery/AKM_native_candidate.mp4` contains the warm-cache switch-back equip with actual mixer audio. `AKM_EquipCharge_Editable.blend` preserves the editable action and current Fab wood/metal source materials.

