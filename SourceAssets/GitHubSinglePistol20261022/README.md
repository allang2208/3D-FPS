# GitHub single-pistol source integration

User-selected source: https://github.com/ZenXChaos/ThirdPersonShooter-AnimationSets
Commit: `f19adc2ece4cab0f89c9236223abb97d4d2badea`. Repository declares Unlicense; original README/license and downloaded FBX are retained in `../PistolSourceSearch20261022/GitHubCandidate/`.

Scope: third-person right-primary and lone left-primary pistol idle/fire/reload. Preserve first-person assets, Twinblast dual-pistol family, gameplay reload transactions and action ownership.

The donor FBX files contain weighted points but no polygons, and use legacy FBX 6000. `convert_source.cpp` uses the engine's Autodesk FBX SDK to retain the original animation channels and produce FBX 2014. It adds an identity skeleton parent and tiny rigid triangles only to host an importable source skeleton. This proxy is an authoring aid, never the player body. `SourceV2` persists the generated USkeleton explicitly; the initial `Source` attempt lacked this dependency and is not published.

`import_source.py` imports eleven original takes with frame-boundary rounding for the legacy 0.799992 / 0.533328 second tails. `retarget_source.py` maps complete FK spine, clavicle/arm, neck and finger chains to Jason, with IK operations disabled. No wrist position targets or invented elbow poles are used. `publish.py` owns eleven `SinglePistol.Source.*` leaves only and uses the shared config transaction writer.

Two donor files use different local bone axes: `RevolverReloadEnd` and `RevolverCrouchAimReloadInit`. Importing them onto the Idle skeleton gives plausible source joint positions but incompatible local rotations for FK retargeting. `repair_end_bind.py` gives each an independent source skeleton/IK Rig/Retargeter, and `publish.py` requires those two corrected receipts. The original common-bind retargets of these two clips are authoring failures, not runtime choices in the final publication.

Runtime uses the source upper body, the source firing delta and Init/Loop/End reload phases on the existing replicated action clock. Left-primary mirrors the complete local chains in their native bind frames. Existing viewmodel wrist-target fitting and arm roll reconstruction do not run while this source owns the single-pistol arms. The holding fingers retain the specific gun grip; the operating hand retains source animation fingers.

This source is a revolver family. Ordinary magazine reloads reuse its complete arm gesture with their existing mechanical timing; no claim is made that a generic source supplies exact contact with every magazine, drum, cylinder or speedloader. No runtime, screenshot, geometry or multiplayer acceptance is performed by this authoring workflow. Build and saved-asset receipts are reported separately.
