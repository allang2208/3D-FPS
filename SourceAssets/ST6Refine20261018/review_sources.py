"""User-requested, scoped offline geometry and ST6 routing review."""
import json,hashlib,runpy
from pathlib import Path
import numpy as np
O=Path(__file__).parent;R=O.parents[1];OLD=O.parent/'ST6Reset20261017'
cfg=json.loads((R/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
runpy.run_path(str(O/'recipe.py'))['apply'](cfg)
item=cfg['items']['ue_st6_sleeves'];rows=[]
for profile,asset in item['rig_meshes'].items():
    source=OLD/'Authored'/f'{profile}_ue_st6_sleeves.json'
    d=json.loads(source.read_text())
    rows.append(dict(profile=profile,asset=asset,source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                     vertices=len(d['positions']),triangles=len(d['triangles']),original_sleeve_preserved=True,
                     material_overrides=item['base_material_overrides'][profile],
                     owner_mesh=item.get('owner_body_meshes',{}).get(profile)))
d=json.loads((O/'collar.json').read_text());p=np.array(d['positions']);f=np.array(d['triangles']);n=np.array(d['normals'])
area=np.linalg.norm(np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]]),axis=1)*.5
world=json.loads((O/'world_shirt.json').read_text());sleeve=json.loads((OLD/'Authored/Jason_ue_st6_sleeves.json').read_text())
preserved=all(world[key][:len(sleeve[key])]==sleeve[key] for key in ('positions','triangles','normals','uv','weights','triangle_materials'))
quality=dict(finite_positions=bool(np.isfinite(p).all()),finite_normals=bool(np.isfinite(n).all()),
             degenerate_triangles=int((area<1e-8).sum()),maximum_edge_cm=float(max(np.linalg.norm(p[f[:,i]]-p[f[:,(i+1)%3]],axis=1).max() for i in range(3))),
             maximum_weight_sum_error=float(max(abs(sum(w.values())-1) for w in d['weights'])),
             missing_bones=sorted({k for w in d['weights'] for k in w}-set(d['bones'])),jason_original_sleeve_data_identical=preserved)
if not quality['finite_positions'] or not quality['finite_normals'] or quality['degenerate_triangles'] or quality['missing_bones'] or not preserved:raise RuntimeError(str(quality))
report=dict(scope='ST6 source geometry, material routing and offline front/back/collar review only',profiles=rows,geometry=quality,
            materials=dict(original_sleeve_pbr='unchanged',body='original ST6 color/normal textures, rest-space triplanar mapping, differential skinned normals, seam and hem height, zoned roughness',texture_lookups=6,new_runtime_textures=0),
            visual_review=['review_front.png','review_back.png','review_collar.png'],
            preview_limit='Blender preview uses approximate micro-bump; UE material uses the original fabric normal map. No in-game rendering or motion test.',
            game_tested=False)
(O/'offline_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'profiles':len(rows),'geometry':quality},indent=2))
