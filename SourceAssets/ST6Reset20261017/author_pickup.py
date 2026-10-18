"""A display shirt assembled from the actual native cloth surface and original sleeves."""
import json,sys
from pathlib import Path
import numpy as np
O=Path(__file__).parent;sys.path.insert(0,str(O))
from recipe import DEST
body=json.loads((O/'Read/Jason.json').read_text())
sleeve=json.loads((O/'Authored/Jason_ue_st6_sleeves.json').read_text())
out=dict(positions=[],triangles=[],uv=[],normals=[],weights=[],triangle_materials=[],
         materials=[sleeve['materials'][0],DEST+'/Materials/MI_ST6Torso_Pickup.MI_ST6Torso_Pickup',DEST+'/Materials/M_ST6NativeFabric.M_ST6NativeFabric'],
         material_slots=['sleeve_st6_generalist','ST6NativeBodyFabric','ST6NativeArmFabric'])
for d,selection,material in ((sleeve,list(range(len(sleeve['triangles']))),0),
        (body,[i for i,m in enumerate(body['triangle_materials']) if m in (0,1,3,8,9)],1)):
    vertices=sorted({v for i in selection for v in d['triangles'][i]});remap={v:i+len(out['positions']) for i,v in enumerate(vertices)}
    out['positions'].extend(d['positions'][v] for v in vertices);out['weights'].extend(d['weights'][v] for v in vertices)
    for i in selection:
        out['triangles'].append([remap[v] for v in d['triangles'][i]]);out['uv'].append(d['uv'][i]);out['normals'].append(d['normals'][i]);out['triangle_materials'].append(2 if material==1 and d['triangle_materials'][i] in (0,1) else material)
p=np.array(out['positions']);center=(p.min(0)+p.max(0))*.5
out['positions']=(p-center).tolist()
out['body_origin']=(np.array(body['bones']['pelvis']['position'])-center).tolist()
out['shoulder_height']=(body['bones']['clavicle_l']['position'][2]+body['bones']['clavicle_r']['position'][2])*.5-body['bones']['pelvis']['position'][2]
(O/'pickup.json').write_text(json.dumps(out,separators=(',',':')))
print('ST6_PICKUP_AUTHORED',len(out['triangles']))
