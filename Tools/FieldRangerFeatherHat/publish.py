"""Register the new feather hat; existing headgear and gameplay remain separate."""
import copy,importlib.util,json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerFeatherHat20261021';D=P/'Content/ColdSteelData'
KEY='ue_ranger_feather_hat';FAMILY='FieldRangerFeatherHat20261021'
spec=importlib.util.spec_from_file_location('ranger_hat_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(spec);spec.loader.exec_module(entries)
saved=json.loads((R/'saved_assets.json').read_text())
if not saved.get('completed'):raise RuntimeError('The complete hat asset set has not been saved')
paths=[D/'items.json',D/'player_body.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,body=[json.loads(t) for t in texts]
if KEY in catalog and catalog[KEY].get('world_mesh')!=saved['pickup']:raise RuntimeError('The new item key is owned by a different asset')
item=copy.deepcopy(catalog.get(KEY,catalog['ue_field_hat']))
item.update(id=KEY,name='野行翎羽帽',desc='为林地斥候缝制的船型帽，以橄榄斜纹布搭配棕色皮革帽带和包边，黄铜羽座固定单支棕灰翎羽。收起的两侧帽檐便于抬臂与观察，适合游猎装束；柔软帽体提供轻便覆盖，缺少硬盔的防护结构。',
    ue_icon='Icons/'+FAMILY+'/'+KEY+'.png',world_mesh=saved['pickup'],world_material='',
    ue_equipment_icon_mesh=saved['icon'],ue_icon_pitch=0,ue_icon_yaw=-90,ue_icon_roll=0)
recipe=dict(skeletal_mesh=saved['mesh'],attach_bone='head',fits=saved['fit'],covers_scalp_hair=False,
    tip_bones=saved['tip_bones'],tip_limit_degrees=5.,tip_frequency_hz=2.8,tip_damping=.8)
new_catalog=entries.replace(texts[0],[KEY],item) if KEY in catalog else entries.insert(texts[0],[],KEY,item)
candidate=copy.deepcopy(body);candidate.setdefault('head_equipment',{})[KEY]=recipe
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Configuration changed while preparing the hat registration; retry')
body_receipt=entries.commit_player_body(paths[1],raw[1],candidate,owned_paths=[('head_equipment',KEY)],producer=__file__)
if paths[0].read_bytes()!=raw[0]:raise RuntimeError('Item catalog changed; head attachment saved, retry item registration')
paths[0].write_bytes((b'\xef\xbb\xbf' if raw[0].startswith(b'\xef\xbb\xbf') else b'')+new_catalog.encode('utf-8'))
for target in [D/item['ue_icon'],D/'Icons'/(KEY+'.png')]:
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/(KEY+'.png'),target)
(R/'published.json').write_text(json.dumps(dict(completed=True,item=item,recipe=recipe,
    source_item_template='ue_field_hat',local_integration=True,git_commit=None,git_push=None,
    integration=dict(equipment_slot='helmet',supported_heads=list(saved['fit']),
        developer_menu=['装备','头部装备','野行翎羽帽'],
        developer_catalog='Source/FPSGAME/Development/ColdSteelDevelopmentTools.cpp:ItemCatalog',
        pickup_consumer='Source/FPSGAME/UI/ColdSteelPickupConsumable.cpp:BuildConsumable equipment branch',
        pickup_physics='Existing AColdSteelPickup BoxComponent root; model bounds; inventory save transaction',
        icon_family_png=item['ue_icon'],icon_cache_png='Icons/'+KEY+'.png',
        icon_texture=saved['icon_texture'],icon_mesh=saved['icon'],
        asset_cook_root='/Game/Characters/ModularOutfit20260924',
        data_staging='FPSGAME.Build.cs RuntimeDependencies Content/ColdSteelData/...',
        first_person_overlay=None,unreal_assets_saved=True,
        first_person_visibility='Existing head-equipment visibility and scalp-hair ownership',
        packaging_run=False),
    runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('RANGER_FEATHER_HAT_PUBLISHED',KEY,flush=True)
