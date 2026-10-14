"""Round-trip the delivered files without changing the author's mesh or rig."""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
expected=json.loads((ROOT/'Reports/rig.json').read_text('utf8'))
report={'exports':[]}
report_path=ROOT/'Reports/export-checks.json'
for filename in ('SK_RootCrown.fbx','RootCrown_Rigged.glb'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path=ROOT/'Exports'/filename
    if path.suffix=='.fbx':bpy.ops.import_scene.fbx(filepath=str(path))
    else:bpy.ops.import_scene.gltf(filepath=str(path))
    # The glTF importer creates an unskinned bone-display icosphere; it is not
    # present in the file payload and must not be counted as creature geometry.
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'
            and any(m.type=='ARMATURE' for m in o.modifiers)]
    arm=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    points=np.array([(o.matrix_world@v.co)[:] for o in meshes for v in o.data.vertices])
    tri=sum(len(p.vertices)-2 for o in meshes for p in o.data.polygons)
    rows=[v.groups for o in meshes for v in o.data.vertices]
    item={'file':filename,'triangles':tri,'bones':len(arm.data.bones),
        'height_m':float(np.ptp(points[:,2])),'max_influences':max(len(r) for r in rows),
        'unweighted':sum(not r for r in rows),'weight_sum_error':max(abs(sum(e.weight for e in r)-1.) for r in rows),
        'materials':[s.material.name for o in meshes for s in o.material_slots],
        'crown_bones':sum(b.name.startswith('Crown_') for b in arm.data.bones)}
    print('EXPORT_READ '+json.dumps(item),flush=True)
    report['exports'].append(item)
    report_path.write_text(json.dumps(report,indent=2),encoding='utf8')
    assert tri==expected['triangles'] and item['unweighted']==0
    assert item['max_influences']<=8 and item['weight_sum_error']<1e-5
    assert abs(item['height_m']-1.7)<.0001 and item['crown_bones']==31
report['passed']=True
report_path.write_text(json.dumps(report,indent=2),encoding='utf8')
print('ROOT_CROWN_EXPORTS_CHECKED '+json.dumps(report),flush=True)
