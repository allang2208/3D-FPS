"""Publish the exclusive rune through the existing rune slot and saved module recipe."""
import json,os,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
ID='swift_mana_rune';WEAPON='ue_runebound_warhammer'
M='/Game/Weapons/RuneboundWarhammer20261022/SwiftManaRuneV1/M_RuneboundSwiftRuneSurface.M_RuneboundSwiftRuneSurface'
OPTION={'id':ID,'name':'迅捷魔力符文','tier':'special','weapons':[WEAPON],
 'description':'符文战锤专属。原生刻纹间贯通迅捷的蓝色魔力，细密流光沿锤身涌动。',
 'appearance':'原生刻纹强化 · 蓝色流光 · 密集魔力微粒',
 'stats':{'attack_speed_mult':1.1},'effects':[{'text':'攻击速度 +10%','benefit':1}],
 'special_effects':['迅捷苏醒｜符文苏醒所需的有效攻击由10次降为5次；同次群攻仅计一次。',
                    '魔力流光｜强化原生符文的蓝色流光，苏醒时漂浮微粒与锤头命中粒子更密集。']}
TRAIT='符文苏醒：攻击伤及敌人积累能量，蓄满后自动激活20秒；基础需10次有效攻击，迅捷魔力符文改为5次。同次群攻仅积累一次。'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def apply(catalog,bench):
    saved=read(P.parent/'PassiveV1/import_receipt.json')['native_material_slots']
    names={name for values in saved.values() for name in values}
    catalog['slots'].setdefault('rune',{})[ID]={'appearance':OPTION['appearance'],'surface_materials':{name:M for name in sorted(names)}}
    column=next(c for c in bench['columns'] if c['key']=='rune')
    column['options']=[o for o in column.get('options',[]) if o.get('id')!=ID]+[OPTION]
    column['description']='在原生刻纹上装配特殊魔力符文，或在长柄附加通用符文。'
    for trait in bench.get('traits',[]):
        if trait.get('text','').startswith('符文苏醒：'):trait['text']=TRAIT
    return catalog,bench
def publish():
    if not read(P/'import_receipt.json').get('complete'):raise RuntimeError('Save the Swift material first')
    icon=P/'Export/ue_runebound_warhammer_blade_2_swift_mana_rune.png'
    if not icon.exists():raise RuntimeError('Author the exclusive rune icon first')
    cp=DATA/'runebound-warhammer-modules.json';bp=DATA/'runebound-warhammer-gunsmith.json'
    before={p:p.read_bytes() for p in (cp,bp)}
    catalog,bench=apply(*(json.loads(before[p].decode('utf-8-sig')) for p in (cp,bp)))
    (P/'Before').mkdir(exist_ok=True)
    for path,obj in ((cp,catalog),(bp,bench)):
        backup=P/'Before'/path.name
        if not backup.exists():backup.write_bytes(before[path])
        if path.read_bytes()!=before[path]:raise RuntimeError('Concurrent write '+str(path))
        tmp=path.with_name(path.name+'.swift-mana.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,path)
    for path,obj in ((P.parent/'ModulesV1/catalog_base.json',catalog),(P.parent/'ModulesV1/workbench.json',bench)):
        path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copy2(icon,DATA/'AttachmentIcons20260913'/icon.name)
    (P/'publication_receipt.json').write_text(json.dumps({'complete':True,'weapon':WEAPON,'slot':'rune','option':ID,'tier':'special','tested':False},indent=2),encoding='utf-8')
    print('RUNEBOUND_SWIFT_MANA_RUNE_PUBLISHED')
if __name__=='__main__':publish()
