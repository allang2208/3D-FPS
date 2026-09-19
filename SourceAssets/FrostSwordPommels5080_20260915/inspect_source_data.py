"""Read source mesh/texture authoring data for the three reported defects."""
import bpy, json, struct, sys
from pathlib import Path
from collections import Counter
import numpy as np
P=Path(__file__).parent
result={}
for key in ['ballast_hardened','ballast_rune','ballast_magic_orb']:
    bpy.ops.wm.open_mainfile(filepath=str(P/key/'FrostPommel_Editable.blend'))
    row={}
    for name in ['SM_FrostPommel_'+key,'Generated_5080_Master','Generated_Game_Body','SM_FrostSword_Pommel_factory']:
        obj=bpy.data.objects[name];d=obj.data
        v=np.array([p.co[:] for p in d.vertices]);edges=Counter()
        for f in d.polygons:
            for a,b in zip(f.vertices,list(f.vertices[1:])+[f.vertices[0]]):edges[tuple(sorted((a,b)))]+=1
        row[name]={'verts':len(v),'faces':len(d.polygons),'bounds':[v.min(0).tolist(),v.max(0).tolist()], 'materials':dict(Counter(d.materials[f.material_index].name for f in d.polygons)), 'boundary_edges':sum(n==1 for n in edges.values()),'uv': [u.name for u in d.uv_layers]}
    raw=(P/key/'textured_master_00001_.glb').read_bytes();n,t=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+n]);offset=20+n+8
    (P/key/'source_glb.json').write_text(json.dumps(doc,indent=2))
    for idx,img in enumerate(doc.get('images',[])):
        bv=doc['bufferViews'][img['bufferView']];start=offset+bv.get('byteOffset',0)
        (P/key/f'embedded_{idx}.png').write_bytes(raw[start:start+bv['byteLength']])
    row['glb_materials']=doc.get('materials')
    result[key]=row
(P/'source_defect_data.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2),flush=True)
