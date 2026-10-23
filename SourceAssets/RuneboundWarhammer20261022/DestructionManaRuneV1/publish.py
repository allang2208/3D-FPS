"""Publish the second exclusive magic rune without replacing other weapon edits."""
import json,os,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
ID='destruction_mana_rune';WEAPON='ue_runebound_warhammer'
M='/Game/Weapons/RuneboundWarhammer20261022/DestructionManaRuneV1/M_RuneboundDestructionRuneSurface.M_RuneboundDestructionRuneSurface'
OPTION={'id':ID,'name':'破坏魔力符文','tier':'special','weapons':[WEAPON],
 'description':'符文战锤专属。蓝紫魔力沿原生刻纹相向汇聚，苏醒时迸出亮白裂光。',
 'appearance':'原生刻纹强化 · 蓝紫聚能 · 破碎光核',
 'stats':{'intelligence_mult':1.1,'wisdom_mult':1.1},
 'effects':[{'text':'精神 +10%','benefit':1},{'text':'智力 +10%','benefit':1}],
 'special_effects':['破坏苏醒｜符文苏醒期间，该被动提供的附加魔法伤害翻倍；苏醒仍需10次有效攻击，持续20秒。',
                    '聚能崩解｜原生刻纹汇聚蓝紫魔力并迸出裂光，苏醒命中时在锤头散出上浮的魔力碎片。']}

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def apply(catalog,bench):
    saved=read(P.parent/'PassiveV1/import_receipt.json')['native_material_slots']
    names={name for values in saved.values() for name in values}
    catalog['slots'].setdefault('rune',{})[ID]={'appearance':OPTION['appearance'],'surface_materials':{name:M for name in sorted(names)}}
    column=next(c for c in bench['columns'] if c['key']=='rune')
    column['options']=[o for o in column.get('options',[]) if o.get('id')!=ID]+[OPTION]
    column['description']='在原生刻纹上装配特殊魔力符文，或在长柄附加通用符文。'
    return catalog,bench

def publish():
    if not read(P/'import_receipt.json').get('complete'):raise RuntimeError('Save destruction rune assets first')
    icon=P/'Export/ue_runebound_warhammer_blade_2_destruction_mana_rune.png'
    if not icon.exists():raise RuntimeError('Author destruction rune icon first')
    cp=DATA/'runebound-warhammer-modules.json';bp=DATA/'runebound-warhammer-gunsmith.json'
    before={p:p.read_bytes() for p in (cp,bp)}
    import runpy
    catalog,bench=runpy.run_path(str(P.parent/'SwiftManaRuneV1/publish.py'))['apply'](
        *(json.loads(before[p].decode('utf-8-sig')) for p in (cp,bp)))
    catalog,bench=apply(catalog,bench)
    (P/'Before').mkdir(exist_ok=True)
    for path,obj in ((cp,catalog),(bp,bench)):
        backup=P/'Before'/path.name
        if not backup.exists():backup.write_bytes(before[path])
        if path.read_bytes()!=before[path]:raise RuntimeError('Concurrent write '+str(path))
        tmp=path.with_name(path.name+'.destruction-mana.tmp')
        tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,path)
    for path,obj in ((P.parent/'ModulesV1/catalog_base.json',catalog),(P.parent/'ModulesV1/workbench.json',bench)):
        path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copy2(icon,DATA/'AttachmentIcons20260913'/icon.name)
    (P/'publication_receipt.json').write_text(json.dumps({'complete':True,'weapon':WEAPON,'slot':'rune','option':ID,
        'tier':'special','swift_attack_speed_mult':1.1,'destruction_attribute_mult':1.1,'destruction_awakening_mult':2.,'tested':False},indent=2),encoding='utf-8')
    print('RUNEBOUND_DESTRUCTION_MANA_RUNE_PUBLISHED')
if __name__=='__main__':publish()
