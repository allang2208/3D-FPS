import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;D=json.loads((O/'capture.json').read_text());C=json.loads((O/'production.json').read_text());R={}
def signature(ob,body,allmesh=False):
 me=ob.data;p=np.asarray([tuple(ob.matrix_world@v.co) for v in me.vertices]);faces=[f for f in me.polygons if allmesh or f.material_index!=body];out=[]
 for f in faces:out.append(tuple(sorted(tuple(np.round(p[i],7)) for i in f.vertices)))
 return sorted(out)
for key,row in D['assets'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=row['export']);old=next(o for o in bpy.context.scene.objects if o.type=='MESH')
 with bpy.data.libraries.load(C['assets'][key]['blend'],link=False) as (a,b):b.objects=a.objects
 ob=next(o for o in b.objects if o and o.type=='MESH');before=signature(old,C['assets'][key]['body_slot'],key=='LMG201');after=signature(ob,C['assets'][key]['body_slot'],key=='LMG201')
 exact=before==after;R[key]={'triangles':len(before),'positions_equal_at_0_0001_mm':exact,'scope':'whole asset' if key=='LMG201' else 'all native interface faces'}
 (O/'interface_preservation.json').write_text(json.dumps(R,indent=2));print('PHANTOM_INTERFACE',key,exact,len(before),flush=True)
 if not exact:raise RuntimeError('Interface changed '+key)
