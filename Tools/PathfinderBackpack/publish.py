"""Publish this saved backpack only; inventory and player saves are never reset."""
import hashlib,json,os,runpy,tempfile
from pathlib import Path
from PIL import Image

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/PathfinderBackpack20261023';KEY='ue_pathfinder_backpack'
writer=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))
plan=json.loads((R/'manifest.json').read_text());saved=json.loads((R/'saved_assets.json').read_text())
if not saved.get('completed') or saved['revision']!=plan['revision']:
    raise RuntimeError('Save all current backpack assets before publication')
for row in plan['variants']:
    rec=saved['variants'][row['profile']]
    if not rec['saved'] or rec['sha256']!=hashlib.sha256(Path(row['source']).read_bytes()).hexdigest():
        raise RuntimeError('Unsaved harness '+row['profile'])
for key in ['Display','Worn']:
    if not saved.get(key,{}).get('saved'):raise RuntimeError('Missing saved '+key)
    folder=R/'Authored'/key
    digest=hashlib.sha256(b''.join((folder/(n+'.bin')).read_bytes() for n in ['positions','normals','uv','triangles','materials'])).hexdigest()
    if saved[key]['sha256']!=digest:raise RuntimeError('Current static buffers not saved: '+key)

image=Image.open(R/'Icon/source_icon.png').convert('RGBA')
image=image.crop(image.getchannel('A').getbbox());image.thumbnail((292,292),Image.Resampling.LANCZOS)
canvas=Image.new('RGBA',(320,320));canvas.alpha_composite(image,((320-image.width)//2,(320-image.height)//2))
icon=P/'Content/ColdSteelData/Icons'/(KEY+'.png');canvas.save(icon)
outfit={
    'world_static_mesh':saved['Display']['asset'],
    'world_mesh':saved['variants']['bare']['asset'],
    'world_mesh_by_shirt':{r['shirt']:saved['variants'][r['profile']]['asset'] for r in plan['variants'] if r['shirt']},
    'rigid_pack':{'mesh':saved['Worn']['asset'],'location':plan['variants'][0]['rigid_location'],'rotation_quat':[0,0,0,1],
                  'location_by_shirt':{r['shirt']:r['rigid_location'] for r in plan['variants'] if r['shirt']}},
    'backpack_motion':plan['backpack_motion']}
config=P/'Content/ColdSteelData/player_body.json';before=config.read_bytes();cfg=json.loads(before.decode('utf-8-sig'))
previous=cfg['outfits'].get(KEY)
if previous and previous!=outfit:
    raise RuntimeError('This item already has a different presentation revision; publish an explicit scoped update')
cfg['outfits'][KEY]=outfit
body_receipt=writer['commit'](config,before,cfg,owned_paths=[('outfits',KEY)],producer=__file__)
item={'id':KEY,'name':'开拓者战术背包','category':'equipment','type':'背包装备','equipSlot':'backpack',
      'stack_max':1,'maxStack':1,'price':260,'grid_w':4,'grid_h':4,
      'bagExtraCells':54,'bagCompartmentCells':72,'bagCompartmentColumns':12,'bagCompartmentRows':6,
      'desc':'野外勘探队使用的模块化战术背包。金属复合承重架与宽腰封分担负重，密封卷装顶仓、工具侧仓和独立夹层适合长途探索与补给搬运。',
      'ue_icon':'Icons/'+KEY+'.png','icon_fallback':'包'}
catalog=P/'Content/ColdSteelData/items.json'
with writer['_lock'](P/'Saved/PathfinderPublication/items.lock'):
    before=catalog.read_bytes();text=before.decode('utf-8-sig');catalog_data=json.loads(text)
    if KEY in catalog_data and catalog_data[KEY]!=item:raise RuntimeError('Existing item tuning differs; preserve current catalog')
    after=writer['_set'](text,(KEY,),item).encode('utf-8')
    if before.startswith(b'\xef\xbb\xbf'):after=b'\xef\xbb\xbf'+after
    backup=R/'Before/items.before-publication.json';backup.parent.mkdir(exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    with tempfile.NamedTemporaryFile(dir=catalog.parent,prefix='.pathfinder-items-',suffix='.tmp',delete=False) as stream:
        temp=Path(stream.name);stream.write(after);stream.flush();os.fsync(stream.fileno())
    try:
        if catalog.read_bytes()!=before:raise RuntimeError('Catalog changed during publication; retry from current data')
        os.replace(temp,catalog)
    finally:
        if temp.exists():temp.unlink()
result=dict(item=KEY,name=item['name'],revision=plan['revision'],status='saved_and_integrated_awaiting_user_gameplay',
            player_body_receipt=body_receipt,main_grid=[18,7],main_cells=126,added_rows=3,added_cells=54,
            compartment_grid=[12,6],compartment_cells=72,unequipped_grid=[4,4],
            icon=str(icon),assets=str(R/'saved_assets.json'),runtime_tested=False,network_tested=False,
            player_saves_modified=False,decimation_applied=False,native_code_changed=False,
            native_presentation='existing per-observer bounded backpack inertia and replicated equipment slots',
            git_commit=None,git_push=None)
(R/'published.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
design=json.loads((R/'design.json').read_text(encoding='utf-8'))
design.update(name=item['name'],status=result['status'],model_created=True,model_source='user_meshy_glb',imported_to_ue=True,
              item_id=KEY,inventory_changed=True,inventory={'bagExtraCells':54,'bagCompartmentColumns':12,'bagCompartmentRows':6},
              source_sha256=json.loads((R/'Input/source.json').read_text())['sha256'],wearable_profiles=6,
              geometry=plan['geometry'],original_source_preserved=True,decimation_applied=False,
              runtime_tested=False,user_accepted_model=False,materials_source='provided GLB PBR; fitted harness uses woven PBR and metal hardware')
(R/'design.json').write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('PATHFINDER_PUBLISHED',KEY,flush=True)
