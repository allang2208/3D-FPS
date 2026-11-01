"""Publish only the Thor-exclusive Coil grip; retain all other options."""
from pathlib import Path
import datetime,json,os,shutil
P=Path(__file__).resolve().parent;R=P.parents[2]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Coil import is incomplete')
build=json.loads((P/'build_receipt.json').read_text(encoding='utf-8-sig'))
if build['exit_code']!=0:raise RuntimeError('Coil gameplay build is incomplete')
backup=P/'Backups'/('Catalog-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=True)
appearance='分段绝缘握持 · 连续铜线圈 · 钛合金护肋与蓝白导光槽'
option=dict(id='coil_grip',name='线圈',tier='special',weapons=['ue_thunder_god_hammer'],
 description='雷神之锤专属。铜绕组收束于钛合金护肋之间，蓝白电荷沿绝缘握柄导流，在重击释放后寻找附近的敌人。',appearance=appearance,
 stats=dict(heavy_charge_speed_bonus=.15,attack_speed_mult=1.10),
 effects=[dict(text='重击蓄力速度+15%',benefit=1),dict(text='攻击速度+10%',benefit=1)],
 special_effects=[
 '线圈放电｜释放蓄满的普通重击时，向自身周围半径30米内的随机敌对目标释放1道闪电。',
 '闪电等级｜按自身闪电等级释放，最低按10级计算；沿用闪电的伤害、传导和感电规则，不消耗额外魔法、不占用主动闪电冷却。',
 '贯雷驻场｜投出时放电一次，随后以场上锤子为中心，每6秒向半径30米内的随机敌对目标释放1道闪电，直至开始召回或锤子消失。切换当前武器不会中断。',
 '疾雷迸发｜每道疾雷在实际落点周围半径10米内随机寻找敌人，释放2道闪电；震霆配重的三道后续落雷也分别触发。两道闪电独立选敌，可以命中同一存活目标。',
 '武器联动｜闪电继承本次重击锁定的雷神之锤符文与配重效果；雷击叠加2层感电，无目标时不产生空击。'])
changes=[]
for file in ('thunder-god-hammer-modules.json','thunder-god-hammer-gunsmith.json'):
    path=R/'Content/ColdSteelData'/file;raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
    if 'modules' in file:
        slots=data['slots']['grip'];before=slots.get('coil_grip')
        item=dict(mesh=receipt['models'][0]['asset'],location_cm=list(slots['factory']['location_cm']),appearance=appearance,
             interface=data['interface'],model_revision='CoilGripV1',source_mesh='SM_ThunderGodHammer_grip_factory',design_reference='CoilGripV1/Design/Coil_ThreeViews.png')
        slots['coil_grip']=item
    else:
        col=next(c for c in data['columns'] if c['key']=='grip');before=next((o for o in col['options'] if o['id']=='coil_grip'),None)
        if before is None:col['options'].append(option)
        else:col['options'][col['options'].index(before)]=option
        item=option
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent catalog change: '+file)
    shutil.copy2(path,backup/file)
    pending=path.with_name(file+'.coil-pending');pending.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(pending,path)
    changes.append(dict(file=str(path),before=before,after=item,backup=str(backup/file)))
(P/'publication_receipt.json').write_text(json.dumps(dict(complete=True,revision='CoilGripV1',changes=changes,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('COIL_CATALOG_PUBLISHED')
