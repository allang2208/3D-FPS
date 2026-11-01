"""Publish only Static Field's grip option and exact native module mount."""
from pathlib import Path
import datetime,json,os,shutil
P=Path(__file__).resolve().parent;R=P.parents[2]
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt['complete']:raise RuntimeError('Static Field asset import is incomplete')
backup=P/'Backups'/('Catalog-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True,exist_ok=True)
appearance='深棕缝合皮革 · 沉入式双向银纹 · 北欧编结环印'
option=dict(id='static_field_grip',name='静电场',tier='special',weapons=['ue_thunder_god_hammer'],
 description='雷神之锤专属。细银导体沉入缝合皮革，两端以编结锻箍收束，环状雷印将积蓄的电荷向周围释放。',appearance=appearance,
 stats=dict(heavy_charge_speed_bonus=.15,physical_attack_add=5),
 effects=[dict(text='重击蓄力速度+15%',benefit=1),dict(text='物理攻击力+5',benefit=1)],
 special_effects=[
 '静电扩散｜释放蓄满的普通重击时，为自身周围半径30米内的敌对目标叠加2层感电。',
 '贯雷驻场｜投出时释放一次静电，随后以场上锤子为中心，每3秒为半径30米内的敌对目标叠加2层感电，直至开始召回或锤子消失。切换当前武器不会中断。',
 '疾雷激荡｜每道疾雷在实际落点周围半径10米内叠加5层感电；震霆配重由近及远的三道附加落雷分别触发。',
 '感电联动｜仅影响敌对目标；叠层与过载眩晕沿用现有感电规则，并继承回响符文的延长眩晕与保留层数效果。'])
changes=[]
for file in ('thunder-god-hammer-modules.json','thunder-god-hammer-gunsmith.json'):
    path=R/'Content/ColdSteelData'/file;raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
    if 'modules' in file:
        slots=data['slots']['grip'];before=slots.get('static_field_grip')
        item=dict(mesh=receipt['models'][0]['asset'],location_cm=list(slots['factory']['location_cm']),appearance=appearance,
                  interface=data['interface'],model_revision='StaticFieldGripV1',source_mesh='SM_ThunderGodHammer_grip_factory',design_reference='StaticFieldGripV1/Design/StaticField_ThreeViews.png')
        slots['static_field_grip']=item
    else:
        col=next(c for c in data['columns'] if c['key']=='grip');before=next((o for o in col['options'] if o['id']=='static_field_grip'),None)
        if before is None:col['options'].append(option)
        else:col['options'][col['options'].index(before)]=option
        item=option
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent catalog edit; preserved: '+file)
    shutil.copy2(path,backup/file)
    pending=path.with_name(file+'.static-field-pending');pending.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(pending,path)
    changes.append(dict(file=str(path),before=before,after=item,backup=str(backup/file)))
(P/'publication_receipt.json').write_text(json.dumps(dict(complete=True,revision='StaticFieldGripV1',changes=changes,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('STATIC_FIELD_CATALOG_PUBLISHED')
