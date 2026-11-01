"""Register only the newly saved Thor-exclusive Ji Lei modification."""
import datetime,hashlib,json,os,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
models=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
motion=json.loads((P/'motion_ui_receipt.json').read_text(encoding='utf-8'))
if not models['complete'] or not motion['complete']:raise RuntimeError('Save assets before registering modification')
appearance=models['models'][0]['appearance']
option=dict(id='ji_lei_seat',name='疾雷锤座',tier='legendary',weapons=['ue_thunder_god_hammer'],
    description='雷神之锤专属。三路嵌银雷纹汇入原厂圆徽，低矮引雷尖收束雷能；单手举锤蓄力，指向地面召下疾雷。',
    appearance=appearance,stats={'attack_speed_mult':1.2},effects=[{'text':'攻击速度+20%','benefit':1}],special_effects=[
    '疾雷召引｜按住普通攻击键，右手逐渐单手举起战锤，锤身雷电环绕。蓄满后显示地面范围指示器；松开按键，在选定落点降下粗壮雷柱。',
    '落雷轰击｜最远20米，半径3米，将当前完整重击伤害转为魔法伤害，并附加2层感电和1.5秒眩晕。精英控制遵循破韧规则。',
    '持续引雷｜蓄力每秒消耗8点体力和6点魔法；体力消耗受装备消耗倍率影响。资源耗尽时中止蓄力，蓄满前松开仍为普通攻击。',
    '感电过载｜每层增加3%受到的电系伤害；累积5层时清空感电并触发过载，对周围目标放电，过载眩晕1.2秒。'])
module=dict(mesh=models['models'][0]['mesh'],location_cm=[0,0,0],appearance=appearance,
    interface='thunder_god_hammer_modular_v1',model_revision='JiLeiSeatV1',source_mesh='SM_ThunderGodHammer_head_mount_factory',
    design_reference='JiLeiSeatV1/Design.png')
backup=P/'Backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True)
receipt={'complete':False,'changes':[],'runtime_tested':False,'git_commit':None,'git_push':None}
for file in ('thunder-god-hammer-gunsmith.json','thunder-god-hammer-modules.json'):
    path=R/'Content/ColdSteelData'/file;before=path.read_bytes();data=json.loads(before.decode('utf-8-sig'))
    if 'gunsmith' in file:
        options=next(c for c in data['columns'] if c['key']=='head_mount')['options']
        old=next((o for o in options if o['id']=='ji_lei_seat'),None)
        if old:raise RuntimeError('Ji Lei was independently registered; preserve current entry')
        options.append(option)
    else:
        if 'ji_lei_seat' in data['slots']['head_mount']:raise RuntimeError('Ji Lei module already exists')
        data['slots']['head_mount']['ji_lei_seat']=module
    if path.read_bytes()!=before:raise RuntimeError('Concurrent configuration change: '+file)
    shutil.copy2(path,backup/file)
    pending=path.with_name(path.name+'.jilei-pending')
    pending.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(pending,path)
    receipt['changes'].append(dict(file=str(path),before_sha256=hashlib.sha256(before).hexdigest(),after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),owned_id='ji_lei_seat'))
receipt['complete']=True
(P/'publication_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('JI_LEI_CATALOGUE_REGISTERED',flush=True)
