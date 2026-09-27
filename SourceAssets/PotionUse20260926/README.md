# Potion drink / discard source

Current runtime bottles are the four tiers in `../PotionTiersBlender20260926/`.
This directory retains the original split-bottle pipeline and V7 action editing reference.
The final two grip-only JSON adjustments were not rebaked into these older action blends;
use `Content/ColdSteelData/potion_use_motion.json` for the current runtime pose.

Existing owned potion models: `../Consumables5080_20260910/{hp,mp}_potion_editable.blend`.
Accepted visible hand: `../ModularOutfit20260925/BarePalmV7/Editable/AKM_BareArmsV7.blend`.
AKM entry grip: `../RifleMagazineGrip20260922/FingerContactV3/AKM/standard/base/A_AKM_reload.blend`.
Grip method: `../AKMDrumFreeDrop20260920/contact_fit.json` (PalmGripV3) and the current AKM magazine thumb treatment documented in `Docs/Weapons/akm-a762-reload-thumb-twist-20260925.md`.

Run `prepare_bottles.py`, then `author_left_hand.py` with Blender in background. Import the six derived static meshes using `import_bottles.py` in the project Python commandlet. `Content/ColdSteelData/potion_use_motion.json` is authoritative for runtime pose, timing, grip dimensions and hand shape. Native skeleton and current live weapon pose are retained at runtime.

Artifacts: two editable V7 full-action blends, two split-prop blends, six FBX static meshes with explicit UCX collision on shell/stopper, and UE assets under `/Game/Items/Consumables/PotionUse/`. Existing potion assets/materials are references, not replaced outputs. No new external asset or license dependency was introduced.

No preview/render/runtime testing requested or performed.

Publication: scripts and this guide are public; owned input meshes, hand rigs,
Blend/FBX outputs, generated manifests and import receipts remain local. Two
superseded `.blend1` automatic backups were archived to
`trash/potion-publication-20260927/SourceAssets/PotionUse20260926/`; current
editable sources and all required inputs remain in place.

Revision 2: lower the HP palm by 2.0 cm and MP palm by 2.2 cm along the bottle axis using the negative palm-Y anchor, while retaining the authored bottle/rim path. Open the grip for the wider bottle body. Release at 1.76 s, follow-through to 1.80 s, recover in 0.30 s, complete at 2.10 s. Bottle launch velocity is (540, -360, 190) cm/s plus player velocity; finger opening takes 0.08 s. Both editable action blends have been rebaked from the runtime parameters.
