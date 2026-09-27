# Bow equipment / inventory icon

Produced 2026-09-26 from the current retained wooden longbow and WoodSightV12 editable model sources. The PNG shows one unloaded bow, its resting string, and the installed carved wooden sight. No hands, extra ammunition, UI labels, frame, ground, or background are baked into the image.

The whole-item composition follows `skills/ue5-ui-umg-slate/references/runtime-icon-pipeline.md`: authored footprint 4x2 gives 640x320, longest fitted silhouette axis fills 91%, the projected silhouette bounds determine the centre, and aspect is preserved. The bow is physically rotated for a horizontal long axis to match the existing equipment card. It is viewed orthographically from the sight side. There is no 2D mirror. The real string radius and endpoints come from the current bow catalog.

Wood base colour, ORM and normal maps come from the retained `WoodLongbow20260925` texture set. The sight uses the material constants from the V12 importer. String colour/roughness match `ArmsV2/import_parts.py`. Blender Standard colour management, neutral area lighting, and a transparent film are used; engine and offline lighting are not identical. The source asset's existing provenance remains unchanged, and no new external art was downloaded or generated.

`render_icon.py` creates only `Bow_EquipmentIcon.blend` and a 1280x640 supersampled production PNG. `install_icon.py` downsamples with premultiplied alpha and installs `Content/ColdSteelData/Icons/bow_dark.png`, sets `bows.json` `ue_icon=Icons/bow_dark.png`, and raises presentation revision to 24. The existing `NormalizeBowState` migration includes `ue_icon`, so older inventory instances receive the new path on normal profile loading. The user's save files are not modified offline.

Bow is not a runtime `UColdSteelWeaponIcons::Supports` subject, so the existing cached directory-PNG route is the final presentation in equipment, inventory, and warehouse. `FPSGAME.Build.cs` already stages `Content/ColdSteelData/...` as UFS. This change needs no new Texture uasset, editor import, native C++ change, or build.

Backup: `Saved/BowInventoryIcon20260926/Before/bows.json`. Authoring metadata and installation receipt are in this directory. The requested icon has been produced and installed; no game/UI test or separate acceptance rendering was run.
