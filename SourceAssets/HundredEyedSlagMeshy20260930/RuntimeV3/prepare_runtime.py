"""Scoped diagnosis and construction of the game mesh; source high-poly remains intact."""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'PolishV2/HundredEyedSlag_PolishV2.blend'))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
mesh = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
scene = bpy.context.scene
report = {'source_vertices': len(mesh.data.vertices), 'source_triangles': len(mesh.data.polygons), 'actions': {}}
for name in ('A_HundredEyedSlag_Run_V2', 'A_HundredEyedSlag_AttackSweep_R', 'A_HundredEyedSlag_AttackSlam_R'):
    action = bpy.data.actions[name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    bad = []
    folds = []
    for frame in range(int(action.frame_range[0]), int(action.frame_range[1])+1):
        scene.frame_set(frame)
        for kind in ('front', 'rear'):
            for side in ('L', 'R'):
                up, low, palm = [rig.pose.bones[f'{kind}_{part}.{side}'] for part in ('upper','lower','palm')]
                u, l = low.head-up.head, palm.head-low.head
                for bone, vector in ((up,u),(low,l)):
                    error = abs(vector.length/bone.bone.length-1)
                    if error > .001: bad.append({'frame':frame,'bone':bone.name,'length_error_percent':100*error})
                angle = math.degrees(u.angle(l))
                folds.append((angle, frame, kind+'.'+side))
    report['actions'][name] = {'max_segment_error_percent':max((r['length_error_percent'] for r in bad),default=0),
        'worst_fold':max(folds), 'dislocated_samples':len(bad)}
(OUT/'diagnosis_before.json').write_text(json.dumps(report,indent=2))
print('V3_DIAGNOSIS '+json.dumps(report),flush=True)
rig.animation_data.action = None
for pb in rig.pose.bones: pb.matrix_basis = Matrix.Identity(4)
scene.frame_set(1)
for modifier in list(mesh.modifiers): mesh.modifiers.remove(modifier)
mesh.vertex_groups.clear()
bpy.ops.object.select_all(action='DESELECT')
mesh.select_set(True)
bpy.context.view_layer.objects.active = mesh
source_count = len(mesh.data.polygons)
decimate = mesh.modifiers.new('GameLOD0_SurfaceReduction','DECIMATE')
decimate.ratio = 100000/source_count
decimate.use_collapse_triangulate = True
print('V3: reducing source surface to game LOD0',flush=True)
bpy.ops.object.modifier_apply(modifier=decimate.name)
mesh.name = 'SK_HundredEyedSlag_RuntimeV3'
mesh.data.name = 'HundredEyedSlag_GameSurfaceV3'
for poly in mesh.data.polygons: poly.use_smooth = True
armature = mesh.modifiers.new('GameSkin','ARMATURE')
armature.object = rig
mesh.parent = rig
report['game_vertices'] = len(mesh.data.vertices)
report['game_triangles'] = len(mesh.data.polygons)
report['uv_layers'] = len(mesh.data.uv_layers)
(OUT/'geometry_receipt.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_GameSurfaceV3.blend'))
print('V3_GAME_SURFACE_SAVED '+json.dumps({k:v for k,v in report.items() if k!='actions'}),flush=True)
