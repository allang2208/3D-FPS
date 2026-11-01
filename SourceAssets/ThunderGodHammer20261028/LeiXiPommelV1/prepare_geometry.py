import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as(a,b):
    b.objects=['SM_ThunderGodHammer_pommel_factory']
o=b.objects[0];bpy.context.collection.objects.link(o)
v=np.array([tuple(x.co) for x in o.data.vertices]);w=np.array([tuple(o.matrix_world@x.co) for x in o.data.vertices])
report=dict(object=o.name,matrix=[list(x) for x in o.matrix_world],local_bounds=[v.min(0).tolist(),v.max(0).tolist()],world_bounds=[w.min(0).tolist(),w.max(0).tolist()],materials=[m.name for m in o.data.materials],profiles=[])
for z in np.linspace(v[:,2].min(),v[:,2].max(),16):
    sample=v[np.abs(v[:,2]-z)<.0025]
    if len(sample):report['profiles'].append(dict(z=float(z),min=sample.min(0).tolist(),max=sample.max(0).tolist()))
(P/'factory_interface.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
