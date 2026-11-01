import bpy,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).resolve().parent;SRC=O.parent/'M24CustomScope20261026'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SRC/'Donor/Source/source/arms@sniper.fbx'))
s=bpy.context.scene;r=bpy.data.objects['Armature'];C=Matrix.Rotation(math.pi,4,'Z')
out={'objects':{o.name:{'type':o.type,'matrix':[list(v) for v in o.matrix_world]} for o in s.objects},'frames':{}}
for f in [1,25,40,50,70,98,125,148]:
    s.frame_set(f);bpy.context.view_layer.update()
    out['frames'][str(f)]={n:[list(v) for v in C@r.matrix_world@r.pose.bones[n].matrix] for n in ('R_arm','R_elbow','R_wrist','L_arm','L_elbow','L_wrist','R_middle1','L_middle1')}
    out['frames'][str(f)]['gun']=[list(v) for v in C@bpy.data.objects['sniper'].matrix_world]
(O/'donor_source.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('RAW_DONOR',json.dumps({n:[m[0][3],m[1][3],m[2][3]] for n,m in out['frames']['1'].items()}),flush=True)
