"""Freeze the seven-pack/current-clothing coverage matrix for a scoped fit run."""
import hashlib,json,os
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME')
R=Path(os.environ.get('BACKPACK_FIT_RUN_DIR',P/'SourceAssets/BackpackFit20261024/ContactAuditR1'))
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
R.mkdir(parents=True,exist_ok=True);(R/'Capture').mkdir(exist_ok=True)
body=read(P/'Content/ColdSteelData/player_body.json');modular=read(P/'Content/ColdSteelData/modular_outfits.json');catalog=read(P/'Content/ColdSteelData/items.json')
packs=[key for key,value in catalog.items() if value.get('equipSlot')=='backpack']
rows=[];assets={};rigs={}
def add(path,role):
    row=assets.setdefault(path,{'path':path,'roles':[],'key':hashlib.sha256(path.encode()).hexdigest()[:16]})
    if role not in row['roles']:row['roles'].append(role)
for rig,config,items in [('Jason',body,modular['items']),('Kaitlin',body['body_variants']['kaitlin'],modular['body_variants']['kaitlin']['items'])]:
    shirts={k:v['rig_meshes'][rig] for k,v in items.items() if v.get('slot')==7 and rig in v.get('rig_meshes',{})}
    shirt_surfaces={}
    for key,path in shirts.items():
        paths={path}
        for field in ['pants_fit_meshes','pants_mesh_fit_meshes']:
            paths.update(fit['rig_meshes'][rig] for fit in items[key].get(field,{}).values() if rig in fit.get('rig_meshes',{}))
        shirt_surfaces[key]=sorted(paths)
    pants=set()
    for value in items.values():
        if value.get('slot')!=15:continue
        if rig in value.get('rig_meshes',{}):pants.add(value['rig_meshes'][rig])
        pants.update(fit[rig] for fit in value.get('shoe_fit_meshes',{}).values() if rig in fit)
    rigs[rig]={'body':config['body_mesh'],'shirts':shirts,'shirt_surfaces':shirt_surfaces,'pants':sorted(pants)};add(config['body_mesh'],'body')
    head=config.get('heads',{}).get(config.get('default_head'),{}).get('mesh')
    if head:rigs[rig]['head']=head;add(head,'head')
    for path in pants:add(path,'pants')
    for paths in shirt_surfaces.values():
        for path in paths:add(path,'shirt')
    for key in packs:
        outfit=config['outfits'][key]
        for shirt in ['',*shirts]:
            mapped=outfit.get('world_mesh_by_shirt',{}).get(shirt) if shirt else outfit.get('world_mesh')
            mesh=mapped or outfit.get('world_mesh')
            add(mesh,'pack')
            row={'rig':rig,'item':key,'name':catalog[key]['name'],'shirt':shirt,'body':config['body_mesh'],
                 'garment':shirts.get(shirt),'garment_surfaces':shirt_surfaces.get(shirt,[]),'mesh':mesh,'explicit_mapping':bool(mapped),'outfit':outfit}
            rigid=outfit.get('rigid_pack')
            if rigid:
                row['rigid_mesh']=rigid.get('mesh_by_shirt',{}).get(shirt,rigid['mesh']);add(row['rigid_mesh'],'static')
                row['rigid_location']=rigid.get('location_by_shirt',{}).get(shirt,rigid['location'])
                row['rigid_rotation_quat']=rigid['rotation_quat']
            if 'hanging_pack' in outfit:row['hanging_pack']=outfit.get('hanging_pack_by_shirt',{}).get(shirt,outfit['hanging_pack'])
            rows.append(row)
for source in ['player_body','modular_outfits','items']:
    target=R/(source+'_before.json')
    if not target.exists():target.write_bytes((P/'Content/ColdSteelData'/(source+'.json')).read_bytes())
plan={'scope':'saved reference-pose geometry; seven packs, both rigs, bare and current base shirt routes',
      'rigs':rigs,'rows':rows,'assets':list(assets.values()),'missing_mappings':[{'rig':r['rig'],'item':r['item'],'shirt':r['shirt']} for r in rows if not r['explicit_mapping']],
      'runtime_animation_tested':False,'network_tested':False}
(R/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('BACKPACK_FIT_MATRIX',len(rows),'routes;',len(assets),'unique assets;',len(plan['missing_mappings']),'missing mappings')
