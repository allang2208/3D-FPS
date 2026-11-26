"""Publish only the saved ranger shirt geometry/material revision into current data."""
import copy,hashlib,importlib.util,json,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldRangerTop20261020/TailoredFinish20261021';D=P/'Content/ColdSteelData';KEY='ue_field_sweater'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
s=importlib.util.spec_from_file_location('tailored_json_entries',str(P/'Tools/BrownLeatherSet/json_entries.py'));entries=importlib.util.module_from_spec(s);s.loader.exec_module(entries)
saved=read(R/'saved_assets.json');display=read(R/'display_assets.json');authored=read(R/'authored.json');editable=read(R/'editable.json');materials=read(R/'materials.json');baseline=read(R/'inputs.json')['recipe']
if not all(v.get('completed') for v in (saved,display,authored,editable,materials)):raise RuntimeError('Complete tailored asset saves before integration')
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths];texts=[b.decode('utf-8-sig') for b in raw];catalog,config=[json.loads(t) for t in texts]
item=copy.deepcopy(catalog[KEY]);recipe=copy.deepcopy(config['items'][KEY]);body_rows={row['profile']:row for row in authored['records']}
for field in ('rig_meshes','owner_body_meshes'):
    for rig,old_path in baseline[field].items():
        profile='Owner_'+rig if field=='owner_body_meshes' else rig;row=saved['saved'][KEY+'/'+profile]
        if recipe[field][rig] not in (old_path,row['asset']):raise RuntimeError('Current shirt changed during production: '+profile)
        if profile in body_rows:
            if hashlib.sha256(Path(body_rows[profile]['authored']).read_bytes()).hexdigest()!=row['author_sha256']:raise RuntimeError('Unsaved body geometry '+profile)
        elif row.get('material_revision')!=materials['revision']:raise RuntimeError('Unsaved FP material revision '+profile)
        recipe[field][rig]=row['asset']
item.update(ue_icon='Icons/FieldRangerTop20261020/TailoredFinish20261021/ue_field_sweater.png',world_mesh=display['pickup'],world_material='',ue_equipment_icon_mesh=display['icon'],ue_icon_pitch=0,ue_icon_yaw=-90)
out=[entries.replace(texts[0],[KEY],item),entries.replace(texts[1],['items',KEY],recipe)]
for target in dict.fromkeys([D/item['ue_icon'],D/catalog[KEY]['ue_icon'],D/'Icons/ue_field_sweater.png',D/'Icons/ModularOutfit20260924/ue_field_sweater.png']):
    backup=R/'Before'/('icon-'+'_'.join(target.relative_to(D).parts))
    if target.exists() and not backup.exists():shutil.copy2(target,backup)
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/'ue_field_sweater.png',target)
if any(p.read_bytes()!=b for p,b in zip(paths,raw)):raise RuntimeError('Catalog changed during scoped integration; retry')
for p,before,text in zip(paths,raw,out):p.write_bytes((b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
(R/'published.json').write_text(json.dumps(dict(completed=True,revision='TailoredFinish20261021',surface_revision=materials.get('surface_revision'),material_revision=materials['revision'],geometry_profiles=list(body_rows),material_only_profiles=[p for p in baseline['rig_meshes'] if p not in ('Body','Jason')],materials=materials['materials'],item=item,recipe=recipe,exports=editable['exports'],runtime_tested=False,preview_rendered=False,gameplay_attributes_changed=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('TAILORED_PUBLISHED 3 body meshes, 23 FP material variants, pickup and icon',flush=True)
