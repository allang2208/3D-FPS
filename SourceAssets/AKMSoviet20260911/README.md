# Soviet Assault Rifle replacement

Fab listing: https://www.fab.com/listings/d14e05e8-553a-409a-8df0-7c9a8d2c69f4 (SpatialNeglect). User downloaded the FBX package through Fab; copied from FabLibrary/Soviet_Assault_Rifle-d14e05e8. Local metadata and source hashes are retained under Source and build.json. Listing attributes original geometry to Lamoot under CC0; do not infer the texture redistribution license from that geometry statement. Raw package remains local.

Uses AK47NoSubdiv.fbx (31,020 triangles) and the author's five 4K PBR maps. OpenGL normal green channel is flipped for UE. Source UVs are retained. A uniform 0.985 fit and translation align the magazine well, grip and handguard with the current animation. Connected islands 0/44/83/92 form the magazine, 19 the bolt/charging handle and 33 the trigger; remaining geometry follows WPN_root. Each part is inverse-bound from the existing idle pose to its existing mechanical bone.

M4 SK_Manny_Arms_Export geometry is unchanged and hashed. All source actions are retained with fake users in AKM_Soviet_Editable.blend. Runtime animations remain SourceMatched, with the existing EquipCharge/A_AKM_equip (1.7 seconds, magazine seated and left hand holding throughout). No animation assets, ammo data or player saves were overwritten.

build.py creates editable Blend and skeletal FBX; import.py imports SovietFab mesh and author materials. FPSGAMECharacter now prioritizes SovietFab and routes it to the existing animation family. Previous WalnutFab asset remains available as fallback.

Validation: source idle/reload/empty reload contact renders and textured charge render inspected. build-module-v3.log succeeded after parallel traversal compilation was repaired. import.log emitted SOVIET_IMPORT_PASS; commandlet exit 1 includes existing unrelated startup errors. runtime-akm-soviet-v1.log passed fire, ADS, normal/empty reload, M4 switch/back, warehouse and save; independent readback also passed. Delivery/AKM_native_candidate.mp4 contains actual runtime frames and mixer audio. Runtime contact sheet and source material render are included.

Icon audit 20260911003313-1280.log passed after shader warmup; actual textured icon inspected and copied to Content/ColdSteelData/Icons/ue_akm.png and icon.png. Initial cold icon capture was gray while shaders warmed; only the verified textured capture was published.
