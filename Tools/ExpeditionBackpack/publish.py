"""Publish only the expedition item and its saved outfit assets."""
import json,runpy,os,tempfile,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ExpeditionBackpack20261022';KEY='ue_expedition_backpack'
current=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
if 'backpack_motion' in current.get('outfits',{}).get(KEY,{}):
    raise RuntimeError('Initial expedition publisher superseded by BackpackMotion; publish only intended fields through config_transaction')
writer=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))
manifest=json.loads((R/'manifest.json').read_text());saved=json.loads((R/'saved_assets.json').read_text())
if not saved.get('completed') or saved['revision']!=manifest['revision']:raise RuntimeError('Save the complete current asset set before publication')
for row in manifest['variants']:
    record=saved['variants'][row['profile']]
    if not record['saved'] or record['sha256']!=hashlib.sha256(Path(row['source']).read_bytes()).hexdigest():
        raise RuntimeError('Wearable source has not been saved: '+row['profile'])
# Catalog images are authored by the shared orthographic UE studio.
icon=P/'Content/ColdSteelData/Icons'/f'{KEY}.png'
config=P/'Content/ColdSteelData/player_body.json';before=config.read_bytes();data=json.loads(before.decode('utf-8-sig'))
outfit={'world_static_mesh':saved['static']['asset'],
        'world_mesh':saved['variants']['bare']['asset'],
        'world_mesh_by_shirt':{row['shirt']:saved['variants'][row['profile']]['asset'] for row in manifest['variants'] if row['shirt']}}
# A correctly loaded skeletal mesh owns the world presentation; the complete
# static source remains the display/pickup model and is never rendered twice.
data['outfits'][KEY]=outfit
body_receipt=writer['commit'](config,before,data,owned_paths=[('outfits',KEY)],producer=__file__)
item={'id':KEY,'name':'重装远征背包','category':'equipment','type':'背包装备','equipSlot':'backpack',
      'stack_max':1,'maxStack':1,'price':180,'grid_w':3,'grid_h':4,
      'bagExtraCells':36,'bagCompartmentCells':48,'bagCompartmentColumns':8,'bagCompartmentRows':6,
      'desc':'大容量远征背包，承重框架与加厚肩带、胸带、腰封分担负重。装备后主背包增加两整行（+36格，共108格），独立底仓为8×6共48格。适合多日探索、补给和采集搬运。',
      'ue_icon':'Icons/'+KEY+'.png','icon_fallback':'包'}
catalog=P/'Content/ColdSteelData/items.json'
with writer['_lock'](P/'Saved/ExpeditionBackpackPublication/items.lock'):
    before=catalog.read_bytes();text=before.decode('utf-8-sig')
    # Preserve all existing formatting and unrelated concurrent item entries.
    after=writer['_set'](text,(KEY,),item).encode('utf-8')
    if before.startswith(b'\xef\xbb\xbf'):after=b'\xef\xbb\xbf'+after
    backup=R/'Before/items.before-publication.json';backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    with tempfile.NamedTemporaryFile(dir=catalog.parent,prefix='.expedition-items-',suffix='.tmp',delete=False) as stream:
        temp=Path(stream.name);stream.write(after);stream.flush();os.fsync(stream.fileno())
    try:
        if catalog.read_bytes()!=before:raise RuntimeError('Item catalog changed during publication; retry from current data')
        os.replace(temp,catalog)
    finally:
        if temp.exists():temp.unlink()
result={'item':KEY,'local_config_applied':True,'player_body_receipt':body_receipt,
        'main_grid':[18,6],'main_cells':108,'compartment_grid':[8,6],'compartment_cells':48,'unequipped_grid':[3,4],
        'icon':str(icon),'saved_assets':str(R/'saved_assets.json'),'runtime_tested':False,'accepted_by_user':False,
        'icon_export_pending':True,'icon_export_entry':'Tools/BackpackIcons/run.ps1 -Definitions ue_expedition_backpack',
        'no_additional_decimation':True,'git_commit':None,'git_push':None}
(R/'published.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
design=json.loads((R/'design.json').read_text(encoding='utf-8'))
design.update(status='saved_and_integrated_awaiting_user_gameplay',model_created=True,model_source='user_meshy_glb',
              imported_to_ue=True,runtime_data_changed=True,source_sha256=json.loads((R/'Input/source.json').read_text()).get('sha256'),
              actual_dimensions_cm=json.loads((R/'source_prepared.json').read_text())['dimensions_cm'],runtime_tested=False)
(R/'design.json').write_text(json.dumps(design,ensure_ascii=False,indent=2),encoding='utf-8')
print('EXPEDITION_PUBLISHED',KEY,flush=True)
