"""Publish the saved Special Duty backpack without replacing other catalog entries."""
import hashlib
import json
import os
import runpy
import tempfile
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');ROOT=P/'SourceAssets/SpecialDutyBackpack20261024';R=ROOT/'MeshyFitR1_20261024'
KEY='ue_special_duty_backpack';read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
plan=read(R/'manifest.json');saved=read(R/'saved_assets.json')
if not saved.get('completed') or saved['revision']!=plan['revision']:
    raise RuntimeError('Finish saving the authored Special Duty revision first')
for row in plan['variants']:
    if saved['variants'][row['profile']]['sha256']!=hashlib.sha256(Path(row['source']).read_bytes()).hexdigest():
        raise RuntimeError('Unsaved harness source '+row['profile'])
for kind in ['Display','Worn']:
    folder=R/'Authored'/kind
    digest=hashlib.sha256(b''.join((folder/(n+'.bin')).read_bytes() for n in ['positions','normals','uv','triangles','materials'])).hexdigest()
    if saved[kind]['sha256']!=digest:raise RuntimeError('Unsaved static source '+kind)

writer=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))
config=P/'Content/ColdSteelData/player_body.json';before=config.read_bytes();candidate=json.loads(before.decode('utf-8-sig'));owned=[]
for rig in ['Jason','Kaitlin']:
    rows=[row for row in plan['variants'] if row['rig']==rig];bare=next(row for row in rows if not row['shirt'])
    collection=candidate['outfits'] if rig=='Jason' else candidate['body_variants']['kaitlin']['outfits']
    root=('outfits',KEY) if rig=='Jason' else ('body_variants','kaitlin','outfits',KEY)
    outfit={'world_static_mesh':saved['Display']['asset'],'world_mesh':saved['variants'][bare['profile']]['asset'],
            'world_mesh_by_shirt':{row['shirt']:saved['variants'][row['profile']]['asset'] for row in rows if row['shirt']},
            'rigid_pack':{'mesh':saved['Worn']['asset'],'location':bare['rigid_location'],'rotation_quat':bare['rigid_rotation_quat'],
                          'location_by_shirt':{row['shirt']:row['rigid_location'] for row in rows if row['shirt']}},
            'backpack_motion':plan['backpack_motion_by_rig'][rig]}
    if KEY in collection and collection[KEY]!=outfit:raise RuntimeError('Existing Special Duty presentation differs; preserve it')
    collection[KEY]=outfit;owned.append(root)
body_receipt=writer['commit'](config,before,candidate,owned_paths=owned,producer=__file__)

item={'id':KEY,'name':'特勤重载远征背包','category':'equipment','type':'背包装备','equipSlot':'backpack',
      'stack_max':1,'maxStack':1,'price':480,'grid_w':4,'grid_h':4,'bagExtraCells':90,
      'bagCompartmentCells':84,'bagCompartmentColumns':14,'bagCompartmentRows':6,
      'desc':'特勤勘探分队使用的重载远征背包。分段密封舱收纳工具与补给，环抱框架将负重传向肩架和宽腰封，嵌入式侧仓便于分类取用。适合长距离搬运与持续探索，刚性外框在狭窄通道中需要留意转身空间，导轨和锁扣应定期清理。',
      'ue_icon':f'Icons/{KEY}.png','icon_fallback':'包','world_mesh':saved['Display']['asset']}
catalog=P/'Content/ColdSteelData/items.json'
with writer['_lock'](P/'Saved/SpecialDutyPublication/items.lock'):
    before=catalog.read_bytes();current=json.loads(before.decode('utf-8-sig'))
    if KEY in current and current[KEY]!=item:raise RuntimeError('Existing Special Duty catalog differs; preserve current tuning')
    text=writer['_set'](before.decode('utf-8-sig'),(KEY,),item)
    after=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
    with tempfile.NamedTemporaryFile(dir=catalog.parent,prefix='.special-duty-items-',suffix='.tmp',delete=False) as f:
        temp=Path(f.name);f.write(after);f.flush();os.fsync(f.fileno())
    try:
        if catalog.read_bytes()!=before:raise RuntimeError('Catalog changed during publication; retry from current data')
        os.replace(temp,catalog)
    finally:
        if temp.exists():temp.unlink()

result={'revision':plan['revision'],'status':'saved_and_integrated_awaiting_user_gameplay','item':KEY,'name':item['name'],
        'main_grid':[18,9],'extra_rows':5,'compartment_grid':[14,6],'unequipped_grid':[4,4],
        'capacity_basis':'previous concept draft retained on user model handoff; no other backpack capacity changed',
        'variants':len(plan['variants']),'coverage':plan['coverage'],'player_body_receipt':body_receipt,
        'catalog_added_item':KEY,'geometry':read(R/'source_prepared.json'),'saved_assets':str(R/'saved_assets.json'),
        'mounts':{rig:read(R/('mount_calibration_'+rig+'.json'))['selected'] for rig in ['Jason','Kaitlin']},
        'icon_export_pending':True,'player_saves_modified':False,'runtime_tested':False,'network_tested':False,'native_code_changed':False}
(R/'published.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
design=read(ROOT/'design.json');design.update(name=item['name'],item_id=KEY,status=result['status'],production_revision=plan['revision'],
    implementation_receipt='MeshyFitR1_20261024/published.json',source_dimensions_cm=result['geometry']['dimensions_cm'],
    capacity_proposal={'status':'draft_retained_on_model_handoff_applied',**{k:item[k] for k in ['grid_w','grid_h','bagExtraCells','bagCompartmentCells','bagCompartmentColumns','bagCompartmentRows']}},
    model_created=True,imported_to_ue=True,inventory_changed=True,world_wearable_profiles=len(plan['variants']),user_accepted_model=False,runtime_tested=False)
(ROOT/'design.json').write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SPECIAL_DUTY_PUBLISHED',KEY,len(plan['variants']),'main +5 rows / compartment 14x6 / footprint 4x4',flush=True)
