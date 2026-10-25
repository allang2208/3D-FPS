"""Publish only Storm Drive after saved models and both native builds exist."""
import json,os,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
saved=json.loads((P/'import_receipt.json').read_text('utf-8-sig'))
build=json.loads((P/'build_receipt.json').read_text('utf-8-sig'))
if not saved.get('complete'):raise RuntimeError('Asset save incomplete')
if not all(any(r['target']==t and r['exit_code']==0 for r in build) for t in ('FPSGAMEEditor','FPSGAME')):raise RuntimeError('Native builds incomplete')
part='storm_drive_seat'
option={'id':part,'name':'鸣雷疾驱座','tier':'special',
    'description':'黑铁尖拱包覆竖向导雷音板，暗青铜肋骨和嵌银刻纹收束金色电弧。',
    'appearance':'黑铁拱肋 · 青铜导雷 · 金色电弧',
    'stats':{'heavy_charge_speed_bonus':.35,'attack_speed_mult':1.2,'stamina_mult':1.3},
    'effects':[{'text':'重击蓄力速度 +35%','benefit':1},{'text':'攻击速度 +20%','benefit':1},{'text':'体力消耗 +30%','benefit':-1}],
    'special_effects':['导雷共鸣｜锤座周围持续跳动金色电弧。','镇魂合鸣｜与终律·镇魂钟同时装备时，每次有效命中敌人都会在命中处迸发额外的金色分叉电弧。']}
jobs=[('Content/ColdSteelData/common-hammer-seats.json','option',option)]
for variant,runtime,author,interface in [('Steel','warhammer-modules.json','SteelWarhammer20261014','warhammer_factory_v1'),('Runebound','runebound-warhammer-modules.json','RuneboundWarhammer20261022','runebound_warhammer_modular_v1')]:
    spec=dict(saved['parts'][variant],location_cm=[0,0,0],appearance=option['appearance'],interface=interface,shared_option_library='common-hammer-seats.json',model_revision='StormDriveBuildV1')
    jobs.extend([('Content/ColdSteelData/'+runtime,'model',spec),('SourceAssets/'+author+'/ModulesV1/catalog_base.json','model',spec)])
written=[]
for relative,kind,entry in jobs:
    path=ROOT/relative;before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
    if kind=='model':data['slots']['head_mount'][part]=entry
    else:data['options']=[o for o in data['options'] if o.get('id')!=part]+[entry]
    backup=P/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():backup.write_bytes(before)
    tmp=path.with_suffix('.storm-drive.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if path.read_bytes()!=before:raise RuntimeError('Concurrent change: '+relative)
    os.replace(tmp,path);written.append(relative)
icon='head_mount_'+part+'.png';shutil.copy2(P/icon,ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/icon)
(P/'catalog_option.json').write_text(json.dumps(option,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=P.parent/'StormDriveConceptV2/design.json';data=json.loads(path.read_text('utf-8'))
data.update(status='approved_design_modeled_and_integrated',values_approved=True,model_authored=True,runtime_integrated=True,model_revision='StormDriveBuildV1',user_visual_acceptance=False)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(P/'published.json').write_text(json.dumps({'complete':True,'option':option,'catalogs':written,'saved_assets':saved['assets'],'editor_build':0,'game_build':0,'game_tested':False,'multiplayer_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('STORM_DRIVE_SHARED_SPECIAL_MODIFICATION_PUBLISHED')
