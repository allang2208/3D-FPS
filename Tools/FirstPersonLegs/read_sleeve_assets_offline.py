"""Read saved source geometry only, without any scene/component skinning."""
import json,sys
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/SleeveSpikeRepair20261006/Assets'
R.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_ue import source_snapshot
c=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
paths={}
for item in ['ue_field_sweater','ue_field_sweater_charcoal','ue_chainmail_shirt']:
    recipe=c['items'][item]
    paths[item+'_owner']=recipe['owner_body_meshes']['Jason']
    paths[item+'_world']=recipe['rig_meshes']['Jason']
    paths[item+'_M4']=recipe['rig_meshes']['M4']
paths['capri']=c['items']['ue_smoke_grey_capri']['rig_meshes']['Jason']
rows=[]
for name,path in paths.items():
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing clothing '+path)
    _,data=source_snapshot(mesh)
    data['slots']=[str(m.material_slot_name) for m in mesh.materials]
    (R/(name+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    rows.append(dict(name=name,asset=path,vertices=len(data['positions']),triangles=len(data['triangles'])))
    print('CLOTHING_SOURCE_READ '+name,flush=True)
(R/'index.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('OFFLINE_CLOTHING_SOURCES_READ',flush=True)
