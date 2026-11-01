import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'))
o=bpy.data.objects['SM_ThunderGodHammer_grip_factory']
v=np.array([tuple(o.matrix_world@x.co) for x in o.data.vertices])
profile=[]
for z in np.linspace(-.085,.405,50):
 a=v[np.abs(v[:,2]-z)<.006]
 if len(a):
  center=(np.min(a[:,:2],axis=0)+np.max(a[:,:2],axis=0))/2
  radius=np.quantile(np.linalg.norm(a[:,:2]-center,axis=1),[.5,.9,.99])
  profile.append(dict(z=float(z),center=center.tolist(),radii=radius.tolist()))
(P/'host_contract.json').write_text(json.dumps(dict(object=o.name,location=list(o.location),bounds=[v.min(0).tolist(),v.max(0).tolist()],profile=profile),indent=2))
print('HOST_CONTRACT_SAVED',flush=True)
