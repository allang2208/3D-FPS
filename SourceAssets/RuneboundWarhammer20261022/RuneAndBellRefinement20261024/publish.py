"""Patch only this task's visual fields, preserving mechanics and concurrent entries."""
from pathlib import Path
import json,os
P=Path(__file__).resolve().parent
ROOT=P.parents[2]
D='/Game/Weapons/RuneboundWarhammer20261022/FinalTollV2/'
MESH='SM_RuneboundWarhammer_FinalTollHammerHeads_V2'
APPEARANCES={'swift_mana_rune':'上扬翼纹与菱形主印 · 锤柄蓝色流光',
             'destruction_mana_rune':'碎裂晶核与断环纹 · 锤柄赤红流光'}

def apply(catalog,bench):
    for key,text in APPEARANCES.items():
        catalog['slots']['rune'][key]['appearance']=text
    spec=catalog['slots']['hammer_heads']['final_toll_soul_bell']
    spec.update(mesh=D+MESH+'.'+MESH,model_revision='FinalTollHammerHeadV2',
        appearance='厚壁三拱钟室 · 嵌合青铜纹饰 · 倒角黑铁平砧')
    for name in ('M_FinalToll_PBR_Surface','M_FinalToll_FineInlay_Brass','M_FinalToll_Rune_Energy'):
        spec['materials'][name]=D+name+'.'+name
    for column in bench['columns']:
        if column['key']=='rune':
            column['description']='通用与专属符文均沿金属长柄排列，保留各自纹样和流光。'
        for option in column.get('options',[]):
            key=option.get('id')
            if key in APPEARANCES:
                option['appearance']=APPEARANCES[key]
                if key=='swift_mana_rune':
                    option['description']='符文战锤专属。上扬翼纹簇拥中空菱印，蓝色魔力沿长柄贯通，原生刻纹与细密微粒随之苏醒。'
                else:
                    option['description']='符文战锤专属。破碎晶核与断环刻在长柄表面，赤红能量沿裂纹汇聚，苏醒时迸出爆裂余烬。'
            if key=='final_toll_soul_bell':option['appearance']=spec['appearance']
    return catalog,bench

def publish():
    saved=json.loads((P/'import_receipt.json').read_text('utf-8'))
    if not saved.get('complete') or saved.get('rune_masks')!=2:raise RuntimeError('Save the assets first')
    changes=[]
    for cp,bp in [(ROOT/'Content/ColdSteelData/runebound-warhammer-modules.json',ROOT/'Content/ColdSteelData/runebound-warhammer-gunsmith.json'),
                  (P.parent/'ModulesV1/catalog_base.json',P.parent/'ModulesV1/workbench.json')]:
        before={f:f.read_bytes() for f in (cp,bp)}
        values=apply(*(json.loads(before[f].decode('utf-8-sig')) for f in (cp,bp)))
        for f,value in zip((cp,bp),values):
            backup=P/'Before'/f.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
            if not backup.exists():backup.write_bytes(before[f])
            if f.read_bytes()!=before[f]:raise RuntimeError('Concurrent change '+str(f))
            tmp=f.with_suffix('.rune-bell.tmp')
            tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(tmp,f)
            changes.append(str(f.relative_to(ROOT)))
    (P/'publication_receipt.json').write_text(json.dumps({'complete':True,'catalogs':changes,'assets':saved['assets'],
        'game_tested':False,'editor_ui_started':False,'mechanics_modified':False,'animations_modified':False},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Published rune appearance and Final Toll V2 recipe')

if __name__=='__main__':publish()
