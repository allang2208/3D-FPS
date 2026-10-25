"""Publish only the fit fields owned by this saved revision."""
import json,os,runpy,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=Path(os.environ.get('BACKPACK_FIT_RUN_DIR',P/'SourceAssets/BackpackFit20261024/ContactFitR3'))
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
authored=read(R/'authored.json');saved=read(R/'saved_assets.json');baseline=read(R/'player_body_before.json');plan=read(R/'plan.json')
if not saved.get('completed'):raise RuntimeError('Save every fit asset before publication')
captured=read(R/'captured.json')
for record in captured.values():
    if not set(record['roles']).intersection(['body','shirt','pants','head']):continue
    source=P/'Content'/(record['path'].split('.')[0].removeprefix('/Game/')+'.uasset')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=record['package_sha256']:
        raise RuntimeError('Clothing/body source changed during fitting: '+record['path'])
writer=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))
path=P/'Content/ColdSteelData/player_body.json';before=path.read_bytes();body=json.loads(before.decode('utf-8-sig'));owned=[]
def node(data,keys):
    for key in keys:data=data.get(key,{})
    return data
def assign(keys,value):
    target=body
    for key in keys[:-1]:target=target.setdefault(key,{})
    old=node(baseline,keys[:-1]);current=target.get(keys[-1]);previous=old.get(keys[-1])
    if current!=previous and current!=value:raise RuntimeError('Concurrent owned fit edit: '+str(keys))
    target[keys[-1]]=value;owned.append(keys)
for rig in plan['rigs']:
    prefix=() if rig=='Jason' else ('body_variants','kaitlin')
    for item in dict.fromkeys(row['item'] for row in authored['rows']):
        rows=[row for row in authored['rows'] if row['rig']==rig and row['item']==item]
        if not rows:continue
        root=prefix+('outfits',item);bare=next((row for row in rows if not row['shirt']),None)
        for row in rows:
            entry=saved['meshes'][row['asset']]
            if entry['geometry_sha256']!=hashlib.sha256(Path(row['positions']).read_bytes()).hexdigest():raise RuntimeError('Unsaved authored change '+row['asset'])
            field=root+('world_mesh_by_shirt',row['shirt']) if row['shirt'] else root+('world_mesh',)
            assign(field,entry['asset'])
            if 'rigid_location' in row:
                field=root+('rigid_pack','location_by_shirt',row['shirt']) if row['shirt'] else root+('rigid_pack','location')
                assign(field,row['rigid_location'])
            if 'rigid_mesh' in row:
                field=root+('rigid_pack','mesh_by_shirt',row['shirt']) if row['shirt'] else root+('rigid_pack','mesh')
                assign(field,row['rigid_mesh'])
            if 'hanging_pack' in row:assign(root+('hanging_pack_by_shirt',row['shirt']) if row['shirt'] else root+('hanging_pack',),row['hanging_pack'])
            if 'support' in row and 'hanging_pack' not in row:
                assign(root+('backpack_motion','support_by_shirt',row['shirt']) if row['shirt'] else root+('backpack_motion','support'),row['support'])
        if bare and 'rigid_mesh' in bare:
            assign(root+('rigid_pack','mesh'),bare['rigid_mesh']);assign(root+('rigid_pack','rotation_quat'),bare['rigid_rotation_quat'])
        if bare:assign(root+('backpack_motion','pivot'),bare['motion_pivot'])
        motion=node(body,root+('backpack_motion',))
        assign(root+('backpack_motion','bounds_min'),[min(motion['bounds_min'][axis],*(row['bounds_min'][axis] for row in rows)) for axis in range(3)])
        assign(root+('backpack_motion','bounds_max'),[max(motion['bounds_max'][axis],*(row['bounds_max'][axis] for row in rows)) for axis in range(3)])
receipt=writer['commit'](path,before,body,owned_paths=owned,producer=__file__)
record={'revision':R.name,'status':'saved_and_integrated','variants':len(authored['rows']),'statics':len(authored['statics']),
        'config_receipt':receipt,'inventory_changed':False,'original_sling_preserved':not any('hanging_pack' in row for row in authored['rows']),'runtime_animation_tested':False,'network_tested':False}
(R/'published.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('BACKPACK_FIT_PUBLISHED',len(authored['rows']),flush=True)
