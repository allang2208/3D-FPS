# M870 UC animation adaptation

- Donor repository: https://github.com/Urban-Coalition/UC_Workfiles
- Pinned commit: `fc71558d5cab2fb0b91b2eaf1502ed8fdc36290d`.
- Source directory: `Urban1 Decay/[MAIN]/870`; the original Blend, QC and SMD files are retained under `Original/870`.
- Source animations: `draw`, `fire`, `cycle`, `reloadstart`, `reloadinsert`, `reloadend`, `reloadendCycle`. The QC declares 30 fps. The reload uses the right hand for cartridges and left hand for weapon support.
- The donor did not provide an independent inspection sequence. The installed inspection is newly authored for this project's M870, with staged side presentations and independently solved arms.
- Existing M870 Tactical mesh, materials, V7 arms and cartridge geometry remain from `SourceAssets/M870Tactical20261015/CREDITS.md`; no UC weapon/hand mesh, texture or sound is installed.
- Source animation transforms are adapted to the existing native bind, current weapon grips and 60 fps export clock. Bone lengths, hand geometry and weights are retained.
- No explicit license granting independent-game use or redistribution was found in the selected donor repository. The source and derived animations remain local working assets; this task does not grant commercial/public redistribution rights, and nothing was committed or published.

`acquisition.json` records original-file SHA-256 hashes. `authoring.json` records clips and event times. `install_receipt.json` records the actual saved UE packages. No runtime, visual, audio or multiplayer acceptance is claimed.
