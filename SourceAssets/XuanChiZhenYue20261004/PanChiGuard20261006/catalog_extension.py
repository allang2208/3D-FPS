"""Publish the single fitted exclusive guard without changing other parts or stats."""
from pathlib import Path
import copy,json
P=Path(__file__).resolve().parent;ROOT=P.parents[2]

def update(path,merge):
    before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'));merge(data)
    backup=P/'Before'/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    if path.read_bytes()!=before:raise RuntimeError('Concurrent update preserved: '+str(path))
    temp=path.with_suffix(path.suffix+'.panchi.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)

def install():
    receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
    if not receipt.get('assets_saved'):raise RuntimeError('Save the actual guard assets before exposing the option')
    m=json.loads((P/'guard_manifest.json').read_text(encoding='utf-8'))
    def modules(root):
        row=copy.deepcopy(root['slots']['guard']['factory'])
        row.update({k:copy.deepcopy(m[k]) for k in ['mesh','interface','location_cm','rotation_deg','scale','materials']})
        row['appearance']='原厂青玉中枢 · 左右舒展蟠螭云翼 · 双面铜色实体浮雕与贯通云孔'
        root['slots']['guard'][m['id']]=row
        root['panchi_guard_revision']='PanChiGuard20261006'
    def option(root):
        column=next(c for c in root['columns'] if c['key']=='guard')
        row={'id':m['id'],'name':m['name'],'tier':'special','weapons':['ue_xuanchi_zhenyue'],
             'description':'玄螭镇岳专属护手。保留原厂青玉与蟠螭中枢，亮铜云翼向两侧舒展，卷云护缘环抱双面龙纹浮雕。',
             'appearance':'宽展铜翼 · 贯通云孔 · 原厂青玉与刀根接座',
             'effects':[{'text':'专属外观：双面蟠螭浮雕与延展云翼','benefit':0}], 'stats':{}}
        effect_file=P.parent/'PanChiEffects20261006/effects.json'
        if effect_file.exists():row.update(json.loads(effect_file.read_text(encoding='utf-8')))
        existing=next((r for r in column['options'] if r['id']==m['id']),None)
        if existing:
            # Retain any subsequently authored gameplay; this module owns appearance.
            if existing.get('stats'):
                row['stats']=existing['stats'];row['effects']=existing.get('effects',row['effects'])
            existing.update(row)
        else:column['options'].append(row)
    update(ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json',modules)
    update(ROOT/'Content/ColdSteelData/melee-gunsmith.json',option)
    update(ROOT/'Content/ColdSteelData/whirlwind-temporal-materials.json',lambda data:data.update(receipt['temporal_materials']))
    published=json.loads((ROOT/'Content/ColdSteelData/melee-gunsmith.json').read_text(encoding='utf-8-sig'))
    published_guard=next(r for c in published['columns'] if c['key']=='guard' for r in c['options'] if r['id']==m['id'])
    (P/'catalog_receipt.json').write_text(json.dumps({'complete':True,'weapon':m['weapon'],'slot':'guard','id':m['id'],
        'tier':'special','stats':published_guard.get('stats',{}),'save_contract':'existing gunsmith_parts.guard selection','runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PANCHI_GUARD_CATALOG_SAVED',flush=True)

if __name__=='__main__':install()
