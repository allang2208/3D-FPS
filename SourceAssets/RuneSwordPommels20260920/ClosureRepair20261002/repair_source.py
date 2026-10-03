"""Correct the shared meteor shell and retain the unchanged production sources."""
import bpy, bmesh, json, shutil
from pathlib import Path
P = Path(__file__).parent
SOURCE = P.parent
ROOT = SOURCE.parents[1]
BACKUP = P/'Before'
bpy.context.preferences.filepaths.save_version = 0

files = [SOURCE/'RuneSword_Pommels_Editable.blend', SOURCE/'RuneSword_Pommels_PBR.blend',
         SOURCE/'model_exports.json', SOURCE/'Export/SM_RunePommel_Meteor.fbx',
         SOURCE/'Export/SM_RunePommel_Meteor.glb']
files += list((SOURCE/'Textures/meteor').glob('meteor_*.png'))
files += [ROOT/'Content/Weapons/AzureRunesword20260913/Pommels20260920/Models/SM_RunePommel_Meteor.uasset']
files += list((ROOT/'Content/Weapons/AzureRunesword20260913/Pommels20260920/Textures').glob('T_Pommel_meteor_*.uasset'))
for src in files:
    dest = BACKUP/src.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.exists() and not dest.exists():
        shutil.copy2(src, dest)

receipt = []
for name in ['RuneSword_Pommels_Editable.blend', 'RuneSword_Pommels_PBR.blend']:
    path = SOURCE/name
    bpy.ops.wm.open_mainfile(filepath=str(path))
    body = bpy.data.objects['MeteorBody']
    bm = bmesh.new()
    bm.from_mesh(body.data)
    before = bm.calc_volume(signed=True)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(body.data)
    body.data.update()
    after = bm.calc_volume(signed=True)
    receipt.append({'source': name, 'body_signed_volume_cm3_before': before*1000000,
                    'body_signed_volume_cm3_after': after*1000000,
                    'body_boundary_edges': sum(e.is_boundary for e in bm.edges),
                    'body_faces': len(bm.faces)})
    bm.free()
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print('METEOR_SOURCE_REPAIRED', name, before, after, flush=True)
(P/'source_repair_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
