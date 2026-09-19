# First-person arms replacement — 2026-09-09

## Delivered mesh

`SK_ArmsReplacement_Source.blend` contains `SK_ArmsReplacement_WRAD`, a new
rounded mesh fitted to the existing `SK_AKM_Viewmodel` rest skeleton. Append
this mesh, point its Armature modifier at the destination combined rig, and
hide/remove the previous `SK_FP_CH_Default_Cubic.*` meshes in the export selection.
The rest transforms and animation tracks of the existing skeleton were not
edited by this arms pipeline.

`SK_ArmsReplacement.fbx` is an independent arms-only skeletal export with the
existing skeleton, intended as an alternate import source. Final integrated
weapon/arms import is owned by the AKM replacement pipeline.

The new mesh uses WRAD ARMS by **wriks**, acquired from the author's official
repository: <https://github.com/wwwriks/wrad-arms>.
The matching author page confirms the license and intended FPS use:
<https://wriks.itch.io/wrad-arms>.
License: **CC0 1.0 Universal**; the original complete license is retained in
`WRAD_Original/LICENSE`. The original `.blend`, `.fbx`, `.glb`, author README,
and pale texture are preserved under `WRAD_Original/`.

Original `arms.blend` SHA-256:
`CCBDB02C33CFC028AA51A7082295078B536BB9B411AB02A057B49BEB667ED61C`.

Changes made here:

- Retargeted mesh rest geometry and weights by anatomical arm/finger segments
  to the existing AKM skeleton; retained left/right asymmetry from animation.
- Applied two Catmull-Clark levels to produce 9,842 vertices and rounded
  fingertips, knuckles, wrists, and elbow silhouettes.
- Replaced the source bare-arm appearance with separate olive fabric sleeve
  and charcoal full-finger glove materials. No original WRAD texture is used
  by the new material.
- Kept the editable source cage in the unmodified original download.

The result is a smooth stylized tactical-arm replacement, not a scanned or
photorealistic hand asset. It improves the previous cubic fingers and preserves
the existing animation interface.

## UE material values

| Material | Linear RGB | Roughness | Metallic |
| --- | --- | --- | --- |
| `M_ArmsReplacement_OliveFabric` | 0.085, 0.105, 0.074 | 0.86 | 0 |
| `M_ArmsReplacement_CharcoalGlove` | 0.019, 0.024, 0.026 | 0.64 | 0 |

The Blender-only procedural micro bump is 0.00025 m at strength 0.12.
FBX does not transfer that node network. The UE import script must create the
material color/roughness values explicitly; this delivery does not claim the
procedural bump is migrated to UE.

## Validation

`arms_replacement_validation.json` records PASS for all nine clips, 445 sampled
frames, finite evaluated vertices, every group resolving to an existing bone,
and normalized vertex weights. This check does not assert weapon contact or
runtime gameplay acceptance.

Actual model renders:

- `arms_replacement_idle.png`: original idle grip, frame 1.
- `arms_replacement_reload.png`: original normal reload, frame 24.
- `arms_replacement_reload_empty.png`: original charging/empty reload, frame 52.

The renders use the old AKM only as an existing pose reference. New AKM FBX
fitting, UE screenshots, and contact acceptance belong to the integrated export.

## Fab candidate acquired

**Free Pack - Male Base Mesh**, PolyOne Studio:
<https://www.fab.com/listings/6ea2f53a-fe66-4c16-8a6b-7ffa2037075c>.

Verified in the live Fab UI on 2026-09-09: free, **CC BY 4.0**, 8.7k triangles,
quad topology, UVs, and Blender/FBX files. The listing was added to the user's
Fab library; the final page explicitly displayed **已保存在我的库中**.
`Fab_PolyOne_OfficialPreview.jpg` preserves its official topology preview.
Attribution required if it is later used: "Free Pack - Male Base Mesh by
PolyOne Studio, CC BY 4.0; modified [describe changes]" with source/license links.

The browser reported Blender and FBX downloads as completed, but its exposed
download API did not return an accessible local file. Neither named file was
present in the local Downloads/temp/artifact locations checked. A normal
unauthenticated request to Fab's published download-info URL received a
Cloudflare security check. No cookie extraction or security-check bypass was
performed. Therefore this Fab model is **in the library but not imported**.

Other candidates considered: Ironbelly Animated First Person Arms Pack and
Modular FPS Hands were paid listings, so no purchase was made. Blender Studio's
CC0 human base meshes were also considered; official downloads returned access
errors in this session, so no model from that bundle is claimed as delivered.

## Reproduction

Run the `*arms_replacement*.py` scripts in `Tools/AssetPipeline` with the installed
Blender 5.1 executable. `build` writes the candidate source, `validate` checks all
clips and exports arms-only FBX, and `render` produces the three pose images.
The independent scripts never open UE, change the active level, or restart it.

## Integrated delivery

The combined AKM runtime mesh now includes this arm replacement. Actual UE
captures, ADS alignment and reload/input checks are recorded in
`../GunplayUpgrade/validation.md`; final game previews are under
`../GunplayUpgrade/Preview/`. The static finite-geometry checks above remain
separate from that runtime evidence.
