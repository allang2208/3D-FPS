import bpy,json,numpy as np
from pathlib import Path
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/Authoring/Inputs.blend')
o=bpy.data.objects['Receptionist_SourceBody'];p=np.array([v.co for v in o.data.vertices])
r={}
for z in [.76,.80,.84,.88,.92,.96,1.0,1.08,1.16,1.22,1.30,1.40,1.45,1.48,1.50]:
 cut=max(.23,.40-(z-.85)*.45)
 a=p[(np.abs(p[:,2]-z)<.007)&(p[:,0]>cut)]
 if len(a):r[str(z)]={'count':len(a),'min':a.min(0).tolist(),'max':a.max(0).tolist(),'median':np.median(a,axis=0).tolist()}
print(json.dumps(r,indent=2))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
print('finger centers',json.dumps({b.name:list(rig.matrix_world@b.head_local) for b in rig.data.bones if b.name.endswith('_l') and any(x in b.name for x in ['index','middle','ring','pinky','thumb'])},indent=2))
