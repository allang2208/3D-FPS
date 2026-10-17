# M870 support-grip surface repair

The user rejected the preceding `M870GripADS20261016` result with an in-game screenshot and requested inspection of hip stance, ADS and reload. The previous whole-hand roll retained a grasp that did not fit this fore-end. This revision uses the native V7 hand and native chainmail mesh as the review surfaces.

`fit_grip.py` places the palm beneath the fore-end, aligns the knuckles along it and authors the phalange chains. `optimize_contact.py` fits sampled skinned pads while retaining bone lengths, weights and the native bind. Its cylinders are fitting proxies; `measure_contact.py` separately checks the complete authored hand against the actual pump triangle mesh. The proxy result alone is not visual acceptance.

`author_surface.py` rebuilds the support shoulder/elbow and forearm stations, keeps the elbow below the sight line, unwraps the elbow solution through each clip, and adds only the shoulder displacement needed at the rear pump stroke to reduce wrist bending. The right hand, gun/bolt tracks, reload feed times and action durations retain the preceding UC adaptation. All 13 active roles receive the same grasp to avoid changing hands at transitions.

- Editable source: `M870_SurfaceFit_Editable.blend`.
- Exported animations: `Exports/Animations`.
- Native readback inputs: `m870.json.gz`, `native_arms.json.gz`, `shirt.json.gz`.
- Offline key-frame images: `Review`; the untextured chainmail material is used to judge its actual silhouette, not its appearance.
- Saved-animation UE preview: `capture_saved.py`, output `UEReview`. It evaluates compressed animation and uses the same M4 hip ruler and M870 iron-sight calibration as the runtime. It does not drive gameplay input, camera sway or the inventory.
- Installation: `install.ps1` and `install_animations.py`; exact-path backups are retained in `Before/Animations`. Import completion is recorded only in `install_receipt.json`.

The source mesh, skeleton, shared arms, shared clothing assets, firearm statistics, sound and ammunition logic are unchanged. This folder contains local derived work; existing source attribution and licensing records still apply.

Delivery status is recorded in `delivery.json` after the saved images have been inspected. Author metrics, asset save receipts and gameplay acceptance are separate results.
