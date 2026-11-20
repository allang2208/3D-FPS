"""Publish only saved TS01 world/owner shirt and waist packages."""
import hashlib
import json
from pathlib import Path
import sys
from patrol_shirt_world import BODY_NAMES,ITEM,P,ROOT,WORLD,read,sha
from patrol_shirt_world_join import put
from shoulder_packages import CONFIG,package_path,write_revision

def batches():
    rows=read(WORLD/'routes.json')
    fits=read(WORLD/'Fits/waists.json')['routes']
    for rig in BODY_NAMES:
        selected=[(key,r) for key,r in rows.items() if r['rig']==rig and not r['base']]
        path=WORLD/'Fits'/f'batch-{rig}-00.txt'
        lines=[]
        for key,r in selected:
            if sha(WORLD/'Fits'/fits[key]['grid'])!=fits[key]['sha256']:raise RuntimeError('Waist pattern changed '+key)
            lines.append('|'.join((rows[r['base_key']]['asset'],r['asset'],key)))
        path.write_text('\n'.join(lines)+'\n',encoding='ascii')

def pack_contacts():
    body=read(P/'Content/ColdSteelData/player_body.json')
    catalog=read(P/'Content/ColdSteelData/items.json')
    pairs={}
    for rig in BODY_NAMES:
        cfg=body if rig=='Jason' else body['body_variants']['kaitlin']
        for name in (k for k,v in catalog.items() if v.get('equipSlot')=='backpack'):
            w=cfg['outfits'][name]
            pack=w.get('world_mesh_by_shirt',{}).get(ITEM)
            if not pack:continue
            rigid=w.get('rigid_pack',{}).get('mesh_by_shirt',{}).get(ITEM)
            pairs[rig+'/'+name]=dict(straps=pack,rigid=rigid)
    return pairs

def publish():
    sys.path.insert(0,str(P/'Tools/BrownLeatherSet'))
    from json_entries import replace,span
    routes=read(WORLD/'routes.json');bases=read(WORLD/'base-saved.json');fits=read(WORLD/'Fits/waists.json')['routes']
    saved={};mapping={}
    for key,row in routes.items():
        package=package_path(row['asset'])
        if not package.is_file():raise RuntimeError('Missing saved upper body '+row['asset'])
        path=row['asset']+'.'+row['asset'].split('/')[-1]
        mapping[row['previous']]=path
        if row['base']:
            receipt=bases[key]
            if receipt['package_sha256']!=sha(package):raise RuntimeError('Base changed '+path)
            saved[key]=receipt
        else:
            count=[int(x) for x in (WORLD/'Fits'/(key+'.saved')).read_text(encoding='utf-8-sig').split()]
            saved[key]=dict(asset=path,previous=row['previous'],package_sha256=sha(package),source_sha256=fits[key]['sha256'],base=row['base_key'],
                            triangles_by_lod=count,lod_count=len(count),trousers=fits[key]['pants_sources'])
    backs=pack_contacts()
    put(ROOT/'world-saved.json',dict(assets=saved,waist_pattern='World/Fits/waists.json',backpack_contact_routes=backs,
                                   contact_surface='Native fitted plate carrier is shared by all waist recipes. Backpack straps and rigid loads continue to resolve by the equipped item ID and body.'))
    producer='Tools/ModernTacticalSet/patrol_shirt_world_waists.py'
    before=CONFIG.read_bytes();text=before.decode('utf-8-sig');count=0;seen=set()
    for location in (['items',ITEM],['body_variants','kaitlin','items',ITEM]):
        a,b=span(text,location);part=text[a:b]
        for old,new in mapping.items():
            needle=json.dumps(old);existing=part.count(needle)
            if '/CrouchFit/' in new:
                prior=json.dumps(new.replace('/CrouchFit/','/'))
                count+=part.count(prior)
                part=part.replace(prior,json.dumps(new))
            if existing or json.dumps(new) in part:seen.add(old)
            count+=existing
            part=part.replace(needle,json.dumps(new))
        for field,value in {'appearance_family':'TS01PatrolShirtR2','waist_fit_revision':'PatrolShirtR2-native-waist',
                            'pants_fit_pipeline':producer}.items():
            part=replace(part,[field],value)
        text=text[:a]+part+text[b:]
    if set(mapping)!=seen:raise RuntimeError('Worn shirt routes changed during production')
    if text!=before.decode('utf-8-sig'):
        write_revision(CONFIG,before,(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf8'))
    policy=P/'Tools/GarmentWaist/policies.json'
    original=policy.read_bytes();updated=original.decode('utf-8-sig')
    slots=next(iter(bases.values()))['material_slots']
    outer=[slots.index(name) for name in ('PS_Jersey','PS_Ripstop','PS_Binding')]
    for field,value in {'producer':producer,'source_root':ROOT.relative_to(P).as_posix(),
                        'outer_slots':{'Jason':outer,'Owner_Jason':outer}}.items():
        updated=replace(updated,['shirts',ITEM,field],value)
    if updated!=original.decode('utf-8-sig'):
        write_revision(policy,original,(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+updated.encode('utf8'))
    put(ROOT/'world-published.json',dict(packages=len(saved),lods_per_package=3,fields_replaced=count,assets={key:v['asset'] for key,v in saved.items()},
                                     retained_backpack_pairs=len(backs)))
    print('PATROL_SHIRT_PUBLISHED',len(saved),count,len(backs),flush=True)

if __name__=='__main__':{'batches':batches,'publish':publish}[sys.argv[1]]()
