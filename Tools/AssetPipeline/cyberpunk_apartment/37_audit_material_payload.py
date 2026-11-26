"""Inventory the requested modelling/material payload: finite geometry, UV,
normal streams and referenced images. Does not render or launch the game."""
import importlib.util
import json
from pathlib import Path
import numpy as np
from playable_config import ROOT

spec=importlib.util.spec_from_file_location('geo',Path(__file__).with_name('00_gltf_geometry.py'))
geo=importlib.util.module_from_spec(spec)
spec.loader.exec_module(geo)
geo.EXPORT=str(ROOT/'export')
g=json.loads((ROOT/'export/CyberpunkApartmentPlayable.gltf').read_text())
buffers=geo.load_buffers(g)
rows=[]
for mesh in g['meshes']:
    counts=dict(triangles=0,zero_area_triangles=0,zero_uv_triangles=0,collapsed_uv_triangles=0,
                near_zero_uv_max_geometry_area_m2=0.,nonfinite_values=0,missing_streams=[])
    for prim in mesh['primitives']:
        a=prim['attributes']
        for stream in ('POSITION','NORMAL','TEXCOORD_0'):
            if stream not in a:counts['missing_streams'].append(stream)
        p=geo.read_accessor(g,buffers,a['POSITION'])
        idx=geo.read_accessor(g,buffers,prim['indices']).astype(int).reshape(-1,3)
        t=p[idx]
        area=np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)
        counts['triangles']+=len(idx)
        counts['zero_area_triangles']+=int((area<1e-12).sum())
        for stream in a:
            values=geo.read_accessor(g,buffers,a[stream])
            counts['nonfinite_values']+=int((~np.isfinite(values)).sum())
        if 'TEXCOORD_0' in a:
            uv=geo.read_accessor(g,buffers,a['TEXCOORD_0'])[idx]
            da,db=uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]
            uarea=np.abs(da[:,0]*db[:,1]-da[:,1]*db[:,0])
            counts['zero_uv_triangles']+=int(((uarea<1e-12)&(area>=1e-12)).sum())
            counts['collapsed_uv_triangles']+=int(((uarea==0)&(area>=1e-12)).sum())
            if ((uarea<1e-12)&(area>=1e-12)).any():
                counts['near_zero_uv_max_geometry_area_m2']=max(counts['near_zero_uv_max_geometry_area_m2'],float(area[(uarea<1e-12)&(area>=1e-12)].max()/2))
    rows.append(dict(name=mesh['name'],**counts))
missing_images=[x.get('uri') for x in g.get('images',[]) if 'uri' in x and not (ROOT/'export'/x['uri']).is_file()]
report=dict(meshes=rows,materials=len(g['materials']),images=len(g.get('images',[])),missing_images=missing_images,
            notes=['Zero UV values are recorded per mesh; flat untextured poles/trim are not missing textures.',
                   'CITY_fog is a Blender volume; hidden in UE because glTF carries no volume shader.'])
(ROOT/'material_payload_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(meshes=len(rows),missing_images=missing_images,
    missing_streams=[r['name'] for r in rows if r['missing_streams']],
    nonfinite=sum(r['nonfinite_values'] for r in rows),
    degenerate=sum(r['zero_area_triangles'] for r in rows),
    uv_degenerate=[(r['name'],r['zero_uv_triangles'],r['collapsed_uv_triangles'],r['near_zero_uv_max_geometry_area_m2']) for r in rows if r['zero_uv_triangles']]),indent=2))
