"""Freeze the approved design and actual native binding inputs for this robe."""
import json,hashlib,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
c=read(P/'Content/ColdSteelData/modular_outfits.json');old=read(P/'SourceAssets/ST6SleeveRepair20261018/before.json')
cached={row['profile']:row for row in old['inventory']};rows=[]
for profile in dict.fromkeys(v['rig_profile'] for v in c['profiles'].values()):
    entries=[(key,value) for key,value in c['profiles'].items() if value['rig_profile']==profile]
    sources=list(dict.fromkeys(value.get('native_bare_skin',value['base']) for _,value in entries))
    sources.sort(key=lambda s:(0 if 'WristCoverage' in s else 1,0 if '3cced8ec73' in s else 1))
    if profile in ('Body','Jason'):
        source_file=P/'SourceAssets/ST6Reset20261017/Read'/(profile+'.json');native=read(source_file)
        if native['source'] not in sources:raise RuntimeError('World body source requires new capture '+profile)
        source=native['source']
    else:
        if profile not in cached:raise RuntimeError('New native rig requires capture '+profile)
        paths=[Path(f) for f in cached[profile]['native_variants']]
        source_file=next((f for f in paths if read(f)['source']==sources[0]),None)
        if source_file is None:raise RuntimeError('Native variant requires capture '+profile)
        native=read(source_file);source=native['source']
        actual=hashlib.sha256(disk(source).read_bytes()).hexdigest()
        if native.get('asset_sha256')!=actual:raise RuntimeError('Native geometry changed after capture '+profile)
    rows.append(dict(profile=profile,native=source,file=str(source_file),native_sha256=hashlib.sha256(disk(source).read_bytes()).hexdigest(),source_json_sha256=hashlib.sha256(source_file.read_bytes()).hexdigest(),aliases=[k for k,_ in entries]))
for name in ('items.json','modular_outfits.json','player_body.json'):
    target=R/'Before'/name
    if not target.exists():shutil.copy2(P/'Content/ColdSteelData'/name,target)
(R/'input_inventory.json').write_text(json.dumps(dict(item='ue_blue_mage_robe',rows=rows,approved_concept='Design/blue-mage-robe-concept-v01.png',runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
brief=read(R/'Design/design-brief-v01.json');brief['user_appearance_approved']=True;brief['stage']='approved_for_model_production';(R/'Design/design-brief-v01.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding='utf-8')
print('ROBE_INPUTS_READY',len(rows),'profiles',sum(len(r['aliases']) for r in rows),'registered source paths')
