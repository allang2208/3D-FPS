"""Publish only the Star Oath head into the current model recipe and workbench."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import shutil

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
ID='star_oath_sealing_anvil'
WEAPON='ue_runebound_warhammer'
D='/Game/Weapons/RuneboundWarhammer20261022/StarOathV1/'
MESH='SM_RuneboundWarhammer_StarOathHammerHeads_V1'
ICON=WEAPON+'_hammer_heads_'+ID+'.png'
OPTION={
    'id':ID,'name':'星誓·封界之砧','tier':'legendary','weapons':[WEAPON],
    'description':'符文战锤专属。层叠暗铁包覆成对锤首，旧银护边环抱封印核心，细密符印沿圆环与拱肋流转。',
    'appearance':'层叠暗铁锤甲 · 切面封印核心 · 嵌金符印与导能槽',
    'stats':{'physical_attack_mult':1.1,'magic_attack_mult':1.1},
    'effects':[{'text':'物理攻击力 +10%','benefit':1},{'text':'魔法攻击力 +10%','benefit':1}],
    'special_effects':[
        '封界震荡｜符文苏醒期间，每3次有效攻击命中触发一次爆震，对命中目标及半径2.5米内的敌人造成200%魔法攻击力的魔法伤害。同次群攻只计一次；切换武器、苏醒结束或卸下锤头清空计数。',
        '符文共鸣｜搭配破坏魔力符文，爆震转为赤红且爆震魔法伤害翻倍；搭配迅捷魔力符文，保留5次命中苏醒与攻击速度+10%。',
        '封印绽放｜爆震时锤头核心闪亮，魔力粒子与光屑猛烈炸开，随后减速上浮并缓慢消散。'
    ]
}
SPEC={'mesh':D+MESH+'.'+MESH,'location_cm':[0.,0.,91.6],
      'appearance':OPTION['appearance'],'interface':'runebound_warhammer_modular_v1',
      'model_revision':'StarOathHammerHeadV1','exclusive_to':WEAPON,
      'materials':{name:D+name+'.'+name for name in (
          'M_StarOath_PBR_Surface','M_StarOath_FineInlay_Brass',
          'M_StarOath_Optical_Crystal','M_StarOath_Rune_Energy')}}


def publish():
    imported=json.loads((P/'import_receipt.json').read_text(encoding='utf-8-sig'))
    built=json.loads((P/'build_receipt.json').read_text(encoding='utf-8-sig'))
    if not imported.get('complete') or not imported.get('installed_to_main_project'):
        raise RuntimeError('Finish saving and installing the model/material packages first')
    ready={r['target'] for r in built['targets'] if r['exit_code']==0}
    if not {'FPSGAME','FPSGAMEEditor'}<=ready:
        raise RuntimeError('Finish the necessary Game and Editor builds first')
    source_icon=P/'Icons'/ICON
    if not source_icon.is_file():
        raise RuntimeError('Finish the actual-model framed icon first')
    changes=[]
    for relative,kind in (
        ('Content/ColdSteelData/runebound-warhammer-gunsmith.json','bench'),
        ('Content/ColdSteelData/runebound-warhammer-modules.json','modules'),
        ('SourceAssets/RuneboundWarhammer20261022/ModulesV1/workbench.json','bench'),
        ('SourceAssets/RuneboundWarhammer20261022/ModulesV1/catalog_base.json','modules')):
        path=ROOT/relative
        before=path.read_bytes()
        value=json.loads(before.decode('utf-8-sig'))
        if kind=='bench':
            head=next(c for c in value['columns'] if c['key']=='hammer_heads')
            options=head.setdefault('options',[])
            index=next((i for i,o in enumerate(options) if o.get('id')==ID),None)
            if index is None:
                options.append(OPTION)
            else:
                options[index]=OPTION
        else:
            value['slots']['hammer_heads'][ID]=SPEC
        backup=P/'Before'/relative
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():
            backup.write_bytes(before)
        if path.read_bytes()!=before:
            raise RuntimeError('Concurrent edit; preserve latest '+relative)
        temporary=path.with_name(path.name+'.star-oath.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        os.replace(temporary,path)
        changes.append(relative)
    target=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/ICON
    if target.exists() and target.read_bytes()!=source_icon.read_bytes():
        backup=P/'Before'/target.relative_to(ROOT)
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():
            shutil.copy2(target,backup)
    shutil.copy2(source_icon,target)
    receipt={
        'complete':True,'recorded_at_utc':datetime.now(timezone.utc).isoformat(),
        'weapon':WEAPON,'part':ID,'tier':'legendary','catalogs':changes,
        'saved_assets':imported['assets'],'native_builds':built['targets'],
        'icon':str(target.relative_to(ROOT)),'icon_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'passive':{'physical_attack_multiplier':1.1,'magic_attack_multiplier':1.1,
            'awakening_hits_per_detonation':3,'radius_cm':250.,'magic_attack_coefficient':2.,
            'destruction_detonation_multiplier':2.,'swift_awakening_hits':5,'swift_attack_speed_multiplier':1.1},
        'counting':'one confirmed attack serial, regardless of number of targets',
        'damage':'authority-only deferred independent magic transaction, with friendly and solid-cover filtering',
        'presentation':'one bounded dynamic particle mesh; four burst slots, 384 particles per detonation',
        'saved_selection':'existing gunsmith_parts.hammer_heads field; no save schema change',
        'animations_modified':False,'tests_run':False,'game_started':False,'editor_ui_started':False
    }
    (P/'delivery_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print('STAR_OATH_INTEGRATION_PUBLISHED '+json.dumps({'catalogs':changes,'assets':len(imported['assets']),'icon':str(target)},ensure_ascii=False))


if __name__=='__main__':
    publish()
