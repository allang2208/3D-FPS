"""Persist positive opening speed; native interaction chooses the swing side."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT))
import install as p
u=p.u;p.guard()
world=u.EditorLoadingAndSavingUtils.load_map(p.MAP)
labels={'PowerTheme_'+s['id'] for s in p.interaction_specs(p.SCENE)['doors']}
for actor in p.AA.get_all_level_actors():
    if actor.get_actor_label() in labels:
        actor.modify();actor.set_editor_property('open_angle_degrees',85.0)
if not u.EditorLoadingAndSavingUtils.save_map(world,p.MAP):raise RuntimeError('Upper control door save failed')
receipt=ROOT/'Receipts/install.json';data=json.loads(receipt.read_text('utf8'))
data['door_swing']='Native approach-dependent swing; positive 85 degree speed contract, 0.55 seconds'
receipt.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
readme=ROOT/'README.md'
if readme.exists():
    text=readme.read_text('utf8')
    before='15 个资产及测试地图已保存。UE 随后进入运行状态，最后两扇门的正数开合速度参数待 `finish_doors.py` 补存；源配置已经更新。不要另起 commandlet 覆盖正在运行的地图，结束运行后沿用已有编辑器桥保存。'
    after='15 个资产及测试地图已保存，四扇门的开合参数也已补存。使用原发电区测试地图即可查看本轮布局。'
    readme.write_text(text.replace(before,after),encoding='utf8')
u.log('POWER_UPPER_CONTROL_DOOR_CONFIGURATION_SAVED')
