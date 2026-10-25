"""Requested waist audit: enumerate each current actual mesh pair and viewpoint."""
import json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentWaist20261023'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
inv=read(R/'inventory.json');cfg=read(P/'Content/ColdSteelData/modular_outfits.json')
def exists(path):return bool(path) and (P/'Content'/(path.split('.')[0][6:]+'.uasset')).is_file()
def resolve(shirt,pants,mesh,view,shoe):
    field='owner_body_meshes' if view=='owner' else 'rig_meshes'
    for key,entry in [('actual_mesh',shirt.get('pants_mesh_fit_meshes',{}).get(mesh)),('item',shirt.get('pants_fit_meshes',{}).get(pants)),('default',shirt.get('pants_fit_default'))]:
        path=(entry or {}).get(field,{}).get('Jason')
        if path:return dict(mode='tuck_'+key,shirt=path,pants=mesh,saved=exists(path) and exists(mesh))
    layers=shirt.get('underlayer_meshes',{})
    if mesh in layers:
        path=layers[mesh];top=shirt[field]['Jason']
        return dict(mode='robe_exact_underlayer',shirt=top,pants=path,saved=exists(top) and (not path or exists(path)))
    if shirt.get('pants_underlayer_default'):
        inner=shirt['pants_underlayer_default'];path=inner.get('shoe_fit_meshes',{}).get(shoe,{}).get('Jason') or inner.get('rig_meshes',{}).get('Jason')
        return dict(mode='robe_default',shirt=shirt[field]['Jason'],pants=path,saved=exists(path))
    return dict(mode='unpaired_original',shirt=shirt[field]['Jason'],pants=mesh,saved=exists(shirt[field]['Jason']) and exists(mesh))
rows=[]
for item,shirt in inv['shirts'].items():
    for route in inv['pants_routes']:
        for view in ('world','owner'):
            rows.append(dict(shirt_item=item,pants_item=route['item'],rig=route['rig'],shoe=route['shoe'],mesh=route['asset'],view=view,
                before=resolve(shirt,route['item'],route['asset'],view,route['shoe']),
                after=resolve(cfg['items'][item],route['item'],route['asset'],view,route['shoe'])))
result=dict(scope='Current Jason equipment routes and saved asset files; not animation or gameplay acceptance',
    shirt_count=len(inv['shirts']),pants_count=len(inv['pants']),item_combinations=len(inv['shirts'])*len(inv['pants']),
    unique_pants_meshes=len({r['asset'] for r in inv['pants_routes']}),route_views=len(rows),
    unpaired_before=sum(r['before']['mode']=='unpaired_original' for r in rows),
    unpaired_after=sum(r['after']['mode']=='unpaired_original' for r in rows),
    missing_saved_assets=sum(not r['after']['saved'] for r in rows),rows=rows,runtime_tested=False)
(R/'coverage_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print({k:v for k,v in result.items() if k!='rows'})
