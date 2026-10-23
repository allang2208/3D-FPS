"""Publish saved passive materials and weapon traits without replacing other catalog edits."""
import json,os
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
MAT='/Game/Weapons/RuneboundWarhammer20261022/PassiveV1/M_RuneboundAwakeSurface.M_RuneboundAwakeSurface'
TRAITS=[
 {'icon':'special','text':'符文苏醒：每次攻击伤及敌人积累一格能量，累计十次后自动激活二十秒；同次攻击命中多个敌人只积累一次。'},
 {'icon':'special','text':'苏醒期间符文亮起，攻击附加随智力与精神提升的魔法伤害；期间不再蓄能，结束后重新积累，切换武器或死亡清空。'},
]
def apply(catalog,bench):
    saved=json.loads((P/'import_receipt.json').read_text(encoding='utf-8')).get('native_material_slots',{})
    for choices in catalog['slots'].values():
        for spec in choices.values():
            if spec.get('mesh','').startswith('/Game/Weapons/RuneboundWarhammer20261022/'):
                for slot in saved.get(spec['mesh'],['M_RuneboundWarhammerSurface']):
                    spec.setdefault('materials',{})[slot]=MAT
    texts={t['text'] for t in bench.get('traits',[])}
    for trait in TRAITS:
        if trait['text'].startswith('符文苏醒：') and any(t.startswith('符文苏醒：') for t in texts):continue
        if trait['text'] not in texts:bench.setdefault('traits',[]).append(trait)
    catalog['native_passive']='RuneboundAwakeningV1'
    swift=P.parent/'SwiftManaRuneV1'
    if (swift/'import_receipt.json').exists() and json.loads((swift/'import_receipt.json').read_text(encoding='utf-8')).get('complete'):
        import runpy
        runpy.run_path(str(swift/'publish.py'))['apply'](catalog,bench)
    destruction=P.parent/'DestructionManaRuneV1'
    if (destruction/'import_receipt.json').exists() and json.loads((destruction/'import_receipt.json').read_text(encoding='utf-8')).get('complete'):
        import runpy
        runpy.run_path(str(destruction/'publish.py'))['apply'](catalog,bench)
    return catalog,bench
def publish():
    receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
    if not receipt.get('complete'):raise RuntimeError('Finish passive asset saves before publishing')
    cp=DATA/'runebound-warhammer-modules.json';bp=DATA/'runebound-warhammer-gunsmith.json'
    original={p:p.read_bytes() for p in (cp,bp)}
    catalog,bench=apply(*(json.loads(original[p].decode('utf-8-sig')) for p in (cp,bp)))
    (P/'Before').mkdir(exist_ok=True)
    for path,data in ((cp,catalog),(bp,bench)):
        backup=P/'Before'/path.name
        if not backup.exists():backup.write_bytes(original[path])
        if path.read_bytes()!=original[path]:raise RuntimeError('Concurrent write '+str(path))
        temporary=path.with_name(path.name+'.runebound-passive.tmp')
        temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temporary,path)
    for path,data in ((P.parent/'ModulesV1/catalog_base.json',catalog),(P.parent/'ModulesV1/workbench.json',bench)):
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (P/'publication_receipt.json').write_text(json.dumps({'complete':True,'materials_published':True,'traits_published':True,'tested':False},indent=2),encoding='utf-8')
    print('RUNEBOUND_PASSIVE_RECIPE_PUBLISHED')
if __name__=='__main__':publish()
