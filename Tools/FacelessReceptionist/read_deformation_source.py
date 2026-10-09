import bpy,json,numpy as np
from pathlib import Path
ROOT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\FacelessReceptionist20261007')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/Inputs.blend'))
body=bpy.data.objects['Receptionist_SourceBody'];a=np.array([v.co[:] for v in body.data.vertices]);srcmat=body.matrix_world.copy()
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
donor=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o!=body)
print('DONOR_MATERIALS',[(i,m.name) for i,m in enumerate(donor.data.materials)])
print('INPUT_BONES',json.dumps({b.name:list(rig.matrix_world@b.head_local) for b in rig.data.bones if b.name in ['pelvis','hand_l','lowerarm_l','upperarm_l','foot_l','ball_l','spine_03','head']}))
print('SOURCE_MATRIX',list(map(list,srcmat)))
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V01.blend'))
body=bpy.data.objects['Receptionist_CompleteBody'];p=np.array([v.co[:] for v in body.data.vertices])
ids=np.where((abs(p[:,0])>.26)&(p[:,2]>.68)&(p[:,2]<1.06))[0]
print('ANOMALOUS_COUNT',len(ids))
for i in ids[::max(1,len(ids)//10)]:
 v=body.data.vertices[int(i)]
 print('BAD_VERTEX',json.dumps({'index':int(i),'src':a[i].tolist(),'bind':p[i].tolist(),'weights':[(body.vertex_groups[g.group].name,g.weight) for g in v.groups]}))
print('RAW_BOUNDS',p.min(0).tolist(),p.max(0).tolist())
