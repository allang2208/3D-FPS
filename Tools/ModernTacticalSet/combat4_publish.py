"""Install only new R4 packages, then update the stable TS01 item routes by exact fields."""
import sys,json,copy,hashlib,os,uuid,shutil,ast
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR4';D=P/'Content/ColdSteelData'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
tree=ast.parse((P/'Tools/ModernTacticalSet/shirt_publish.py').read_text(encoding='utf-8'));exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='transaction'],type_ignores=[]),'r4_exact_field_transaction','exec'))

def install(relative):
    source=R/'StageHost/Content'/relative;target=P/'Content'/relative;records=[]
    for file in source.rglob('*'):
        if not file.is_file():continue
        destination=target/file.relative_to(source);digest=sha(file)
        if destination.exists():
            if sha(destination)!=digest:raise RuntimeError('Preserve conflicting package '+str(destination))
        else:
            destination.parent.mkdir(parents=True,exist_ok=True)
            if Path(os.path.realpath(file)).drive.lower()==Path(os.path.realpath(destination.parent)).drive.lower():
                os.link(file,destination)
            else:
                tmp=destination.with_name(destination.name+'.r4-'+uuid.uuid4().hex+'.tmp');shutil.copyfile(file,tmp)
                if sha(tmp)!=digest:raise RuntimeError('Incomplete package copy '+str(tmp))
                os.link(tmp,destination);tmp.unlink()
        records.append(dict(path=str(destination),sha256=digest))
    if not records:raise RuntimeError('No authored packages to install '+relative)
    return records

def main():
    saved=read(R/'saved.json');authored=read(R/'authored.json');art=read(R/'artwork-saved.json');mapping={}
    if not art.get('completed'):raise RuntimeError('Save actual artwork first')
    for row in authored['rows']:
        record=saved['wear'].get(row['asset'],{})
        if record.get('sha256')!=sha(row['file']):raise RuntimeError('Unsaved R4 source '+row['file'])
        old=row['old_asset'].split('.')[0];mapping[old]=record['asset'];mapping[old+'.'+old.rsplit('/',1)[-1]]=record['asset']
    packages=install('Characters/ModularOutfit20260924/ModernTacticalSet20261113/CombatShirtR4');(R/'installed.json').write_text(json.dumps(dict(completed=True,packages=packages),indent=2),encoding='utf-8')
    items_owned=['ue_modern_kevlar_vest','ue_modern_tactical_pants','ue_modern_tactical_gloves','ue_modern_tactical_boots'];cfg=read(D/'modular_outfits.json');edits=[]
    def leaves(value,path):
        if isinstance(value,dict):
            for key,v in value.items():leaves(v,path+[key])
        elif isinstance(value,str) and value in mapping:edits.append((path,mapping[value]))
    def replace(value):
        if isinstance(value,dict):return {k:replace(v) for k,v in value.items()}
        if isinstance(value,list):return [replace(v) for v in value]
        return mapping.get(value,value) if isinstance(value,str) else value
    aliases=0
    for prefix in [['items'],['body_variants','kaitlin','items']]:
        items=cfg
        for key in prefix:items=items[key]
        for item in items_owned:leaves(items[item],prefix+[item])
        for item,recipe in items.items():
            if recipe.get('slot')!=7:continue
            for old,fit in recipe.get('pants_mesh_fit_meshes',{}).items():
                if old in mapping and '/SK_TS01_pants' in old:
                    edits.append((prefix+[item,'pants_mesh_fit_meshes',mapping[old]],replace(copy.deepcopy(fit)) if item=='ue_modern_kevlar_vest' else copy.deepcopy(fit)));aliases+=1
        for field,value in dict(appearance_family='TS01RecutClothR420261115',pants_fit_pipeline='Tools/ModernTacticalSet/combat4_assemble.py',waist_fit_revision='TS01R4-body-clearance-tuck',wear_mode='low_crew_raglan_shirt_with_carrier').items():edits.append((prefix+['ue_modern_kevlar_vest',field],value))
    transaction(D/'modular_outfits.json',edits)
    catalog=read(D/'items.json');edits=[]
    for item in items_owned:
        record=art['items'][item];edits.extend([([item,'world_mesh'],record['pickup']),([item,'ue_equipment_icon_mesh'],record['display'])])
        png=read(R/'artwork.json')['items'][item]['icon']['png']
        for destination in {D/catalog[item]['ue_icon'],D/'Icons'/(item+'.png')}:
            tmp=destination.with_name(destination.name+'.r4-'+uuid.uuid4().hex+'.tmp');shutil.copyfile(png,tmp);os.replace(tmp,destination)
    edits.append((['ue_modern_kevlar_vest','desc'],'土棕色凯夫拉防弹衣搭配男女独立裁片的低圆领作战上衣；弹力胸背、防撕裂插肩袖、圆角袖袋与护肘，自然布料褶皱，袖口和后摆保留搭接。'))
    transaction(D/'items.json',edits)
    transaction(P/'Tools/GarmentWaist/policies.json',[(['shirts','ue_modern_kevlar_vest','producer'],'Tools/ModernTacticalSet/combat4_assemble.py'),(['shirts','ue_modern_kevlar_vest','source_root'],'SourceAssets/ModernTacticalSet20261113/CombatShirtR4')])
    (R/'published.json').write_text(json.dumps(dict(completed=True,wear_assets=len(authored['rows']),packages=len(packages),waist_aliases=aliases,items=items_owned,inventory_regranted=False,backpacks_pending=True,runtime_tested=False,editor_launched=False),ensure_ascii=False,indent=2),encoding='utf-8');print('R4_CLOTHING_INSTALLED_AND_INTEGRATED',flush=True)
if __name__=='__main__':main()
