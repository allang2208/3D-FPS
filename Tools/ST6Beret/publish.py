"""Apply only ST6 beret appearance and its shared head-equipment recipe."""
import json,hashlib,shutil,sys,os
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6Beret20261023/SurfaceV2';D=P/'Content/ColdSteelData';KEY='ue_st6_tactical_helmet'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
saved=read(R/'saved_assets.json')
if not saved.get('completed'):raise RuntimeError('Finish saving all ST6 beret assets')
if hashlib.sha256((R/'Authored/hat.json').read_bytes()).hexdigest()!=saved['author_sha256']:raise RuntimeError('Saved beret source changed')
catalog_path=D/'items.json';body_path=D/'player_body.json';raw=catalog_path.read_bytes();body_raw=body_path.read_bytes();catalog=json.loads(raw.decode('utf-8-sig'));body=json.loads(body_raw.decode('utf-8-sig'))
item=dict(catalog[KEY]);item.update(name='ST6 酒红贝雷帽',desc='ST6 系列酒红羊毛毡贝雷帽，帽冠自然偏垂，黑色皮革帽箍配双道缝线与后部调节绳；暗银 ST6 盾形帽徽带翼纹浮雕，内侧缝制柔软衬里。',ue_icon='Icons/ST6Beret20261023/'+KEY+'.png',icon_fallback='帽',world_mesh=saved['pickup'],world_material='',ue_equipment_icon_mesh=saved['icon'],ue_icon_pitch=0,ue_icon_yaw=-90,ue_icon_roll=0)
# This flag hides the entire scalp groom, including exposed long hair.
recipe=dict(static_mesh=saved['wear'],attach_bone='head',fits=saved['fit'],covers_scalp_hair=False)
existing=body.get('head_equipment',{}).get(KEY)
if existing and existing!=recipe:raise RuntimeError('An ST6 head recipe was added concurrently; retain it for reconciliation')
before=R/'Before';before.mkdir(exist_ok=True)
for name,data in [('items.json',raw),('player_body.json',body_raw)]:
    if not (before/name).exists():(before/name).write_bytes(data)
icon_dir=D/'Icons/ST6Beret20261023';icon_dir.mkdir(parents=True,exist_ok=True)
shutil.copy2(R/(KEY+'.png'),icon_dir/(KEY+'.png'));shutil.copy2(R/(KEY+'.png'),D/'Icons'/(KEY+'.png'))
body.setdefault('head_equipment',{})[KEY]=recipe
body_receipt=entries.commit_player_body(body_path,body_raw,body,owned_paths=[('head_equipment',KEY)],producer=__file__)
text=entries.replace(raw.decode('utf-8-sig'),[KEY],item);out=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
if catalog_path.read_bytes()!=raw:raise RuntimeError('Catalog changed during publication; retain saved body recipe and retry')
temp=catalog_path.with_name('items.st6-beret.tmp');temp.write_bytes(out)
if catalog_path.read_bytes()!=raw:raise RuntimeError('Concurrent catalog writer; retain current catalog')
os.replace(temp,catalog_path)
(R/'published.json').write_text(json.dumps(dict(completed=True,item=item,recipe=recipe,body_receipt=body_receipt,stats_preserved=True,combat_overlay_unchanged=True,runtime_tested=False,git_commit=None,git_push=None),ensure_ascii=False,indent=2),encoding='utf-8')
print('ST6_BERET_PUBLISHED',saved['wear'],flush=True)
