# M24 receiver and independent pistol-grip conversion

Replaces the rejected stock-wrist crop used as an independent grip. The four
replacement grips use actual M4 pistol-grip geometry; the three shared variants
retain their own complete shapes and UV/material sets. Their upper mounting
necks meet one receiver seat without moving the gun's mechanical bones.

The Meshy skeleton stock retains its shape and is refitted between the receiver
hinge and shoulder datum. Native and advanced M24 bodies have separate mating
meshes copied from their actual saved cut boundaries. The advanced lower rear
shell is shortened for the new pistol grip. A 309-face native rear-seat section
allows the factory furniture to restore when the skeleton stock is removed.

`author_geometry.py` produces seven FBX meshes and the editable assembly.
`author_grasp.py` produces two conditional pose profiles. It retains the source
shoulder positions, arm lengths, left arm, weapon and magazine tracks; right-hand
grasp transitions use the pistol-grip donor and existing bolt release windows.
The original base/mag10 profiles remain separate.

`install.py` imports and saves the meshes/material/profile assets, then partitions
only the native receiver faces in the current skeletal asset without reimporting
the arms, clothing morphs or skeleton. Build the ordinary DLL first to expose
`SplitFactoryRearSeat`; `run_assets.ps1 -Stage install` uses the existing UE batch
mutex and a background commandlet when the editor is closed.

Runtime and visual acceptance have not been performed. No gameplay, preview
render, automatic regression or screenshot is part of this delivery.

Delivery: ordinary Editor DLL built successfully in
`Saved/BuildEditor/build-20261031-152031.log`. Seven meshes, one new material,
two conditional pose profiles and the native mesh section were imported and
saved. The imported meshes' degenerate tangent bases were repaired and saved by
`finish_surfaces.py`; see `install_receipt.json` for exact saved asset paths.
