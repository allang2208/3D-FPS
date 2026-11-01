import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).resolve().parent;SRC=O.parent/'M24CustomScope20261026'
def v(v):return [round(x,6) for x in v]
def bounds(values):
    a=np.array(values);return [v(a.min(0)),v(a.max(0))]
# Execute only the in-memory authoring stage to compare intended matrices with saved tracks.
source=(SRC/'author_gameplay.py').read_text()
ctx={'__file__':str(SRC/'author_gameplay.py'),'__name__':'m24_diagnostic'}
exec(compile(source.split('# Use the established dense exporter')[0],str(SRC/'author_gameplay.py'),'exec'),ctx)
names=('clavicle_r','upperarm_r','lowerarm_r','hand_r','clavicle_l','upperarm_l','lowerarm_l','hand_l','WPN_root')
out={'intended':{n:v(ctx['idle'][n].translation) for n in names},
     'source':{n:v(ctx['source'][0][n].translation) for n in ('R_arm','R_elbow','R_wrist','L_arm','L_elbow','L_wrist','WPN_root')},
     'rest':{n:v(ctx['rest'][n].translation) for n in names},
     'bone_flags':{n:{'local':ctx['r'].data.bones[n].use_local_location,'inherit_rotation':ctx['r'].data.bones[n].use_inherit_rotation,'inherit_scale':ctx['r'].data.bones[n].inherit_scale} for n in names}}
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24Repair20261027/M24_Repaired_Editable.blend'),use_scripts=False)
r=bpy.data.objects['M24_V9_Rig'];skin=bpy.data.objects['M24_V9_BareArms'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
out['saved_pose']={n:v(r.pose.bones[n].matrix.translation) for n in names}
out['skin']={'matrix':[list(row) for row in skin.matrix_world],
 'mesh_bounds':bounds([p.co[:] for p in skin.data.vertices]),
 'basis_bounds':bounds([p.co[:] for p in skin.data.shape_keys.key_blocks[0].data]),
 'shape_values':[(k.name,k.value) for k in skin.data.shape_keys.key_blocks if k.value],
 'groups':[(g.index,g.name) for g in skin.vertex_groups]}
(O/'retarget_diagnosis.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in out.items() if k!='skin'},indent=2),flush=True)
