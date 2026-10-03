"""Bounded palm/body surface diagnosis at the right-hand charging phase."""
import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
inputs=json.loads((O/'support_input.json').read_text());body=inputs['body']
bvh=BVHTree.FromPolygons([Vector(v) for v in body['vertices']],body['faces'])
hand=json.loads((O.parent/'RifleMagazineGrip20260922/fit_input.json').read_text())
report={}
for stage,file in [('before','Support_Working.blend'),('after','Support_Draft.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(O/file));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
    s.frame_set(320);bpy.context.view_layer.update();skin=bpy.data.objects['SK_Manny_Arms_Export']
    ev=skin.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    xf=r.pose.bones['WPN_root'].matrix.inverted()@skin.matrix_world;nx=xf.to_3x3().inverted().transposed()
    pad=[];distances={}
    for i,label in zip(hand['indices'],hand['labels']):
        vertex=me.vertices[i];p=xf@vertex.co;near,normal,face,d=bvh.find_nearest(p)
        if d is None:continue
        # Nearest-face normals on overlapping body parts do not define a solid
        # inside test. Record unsigned proximity here; use the separate body
        # envelope analysis for clearance.
        distances.setdefault(label,[]).append(d*1000)
        if label=='hand_l' or 'metacarpal' in label:
            direction=near-p
            if direction.length>1e-6 and (nx@vertex.normal).normalized().dot(direction.normalized())>.4:
                pad.append(d*1000)
    pad.sort()
    report[stage]={'palm_facing_patch_nearest_50_mean_mm':sum(pad[:50])/max(1,len(pad[:50])),
                   'palm_facing_patch_min_mm':pad[0] if pad else None,
                   'minimum_unsigned_surface_distance_by_bone_mm':{n:min(v) for n,v in distances.items()}}
    ev.to_mesh_clear()
    print('SUPPORT_PALM_PROXIMITY',stage,report[stage]['palm_facing_patch_nearest_50_mean_mm'],flush=True)
(O/'contact_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
