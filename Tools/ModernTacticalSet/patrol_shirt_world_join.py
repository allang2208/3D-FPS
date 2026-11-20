"""Join each fitted shirt to its body skin and existing loaded carrier."""
import gc
import sys
from pathlib import Path
import numpy as np
from patrol_shirt_world import BODY_NAMES,GAME,ITEM,MAT,P,R4,ROOT,SET,SHOULDER,WORLD,corrected,read,sha
from shirt_geometry import merge,smooth_transport,subset
from shoulder_packages import package_path
import json

def put(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.writing')
    tmp.write_bytes(json.dumps(data,separators=(',',':'),allow_nan=False).encode())
    tmp.replace(path)

def plan():
    data=read(P/'Content/ColdSteelData/modular_outfits.json')
    rows={}
    for rig in BODY_NAMES:
        cfg=data if rig=='Jason' else data['body_variants']['kaitlin']
        item=cfg['items'][ITEM]
        previous=read(SHOULDER/'published.json')['packages']
        def package(ref):
            return ref.split('.')[0].replace('/CrouchFit/', '/').replace('/PatrolShirtR2/','/ShoulderFit20261118/').replace('SK_TS01_Patrol_', 'SK_TS01_Combat_')
        base=[package(item[key][rig]) for key in ('rig_meshes','owner_body_meshes')]
        tac={package(ref[field][rig]) for pants,ref in item['pants_mesh_fit_meshes'].items() if '/FieldTrousersR2/' in pants for field in ('rig_meshes','owner_body_meshes')}
        for row in read(R4/'authored.json')['rows']:
            if row['rig']!=rig or row.get('kind'):continue
            old=row['asset'].replace('/CombatShirtR4/','/ShoulderFit20261118/');tag=old.rsplit('_',1)[-1]
            ref=old+'.'+old.split('/')[-1]
            dst=GAME+f'/Wear/{rig}/SK_TS01_Patrol_{rig}_{tag}'
            if old in tac:
                dst=dst.replace(f'/Wear/{rig}/',f'/Wear/{rig}/CrouchFit/')
            mode='owner' if row['owner'] else 'world'
            rows[tag]=dict(rig=rig,owner=row['owner'],previous=ref,donor_sha256=previous[ref],asset=dst,base=old in base,
                           tactical=old in tac,legacy=row['file'],source='World/'+f'joined_{rig}_{mode}.json',
                           base_key=base[int(row['owner'])].rsplit('_',1)[-1])
    return rows

def join(rig):
    cloth=read(WORLD/f'shirt_{rig}.json')
    native=read(SET/'CombatShirtR3/Authored'/f'neck_skin_{rig}.json')
    carrier=read(R4/'Authored'/f'vest_{rig}.json')
    original=np.array(carrier['positions'])
    carrier['positions']=corrected(original,rig,'carrier').round(7).tolist()
    smooth_transport(carrier,original)
    for mode in ['world','owner']:
        if mode=='owner':
            # Owner arms are drawn by the weapon-bound sleeves.
            points=np.asarray(cloth['positions']);faces=np.asarray(cloth['triangles'])
            d=subset(cloth,np.abs(points[faces,0]).max(1)<20.)
        else:
            d={k:(v.copy() if isinstance(v,list) else v) for k,v in cloth.items()}
        d.pop('parts',None)
        d['garment_vertex_count']=len(d['positions'])
        merge(d,native);merge(d,carrier)
        put(WORLD/f'joined_{rig}_{mode}.json',d)
        print('PATROL_JOINED',rig,mode,len(d['triangles']),flush=True)
        del d
        gc.collect()

if __name__=='__main__':
    put(WORLD/'routes.json',plan())
    for rig in sys.argv[1:] or BODY_NAMES:join(rig)
