"""Record actual saved assets and compilation separately from user acceptance."""
from pathlib import Path
import json,datetime
O=Path(__file__).parent;P=O.parents[1]
assets=json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
build=json.loads((O/'build_receipt.json').read_text(encoding='utf-8-sig'))
catalog=json.loads((O/'catalog.json').read_text(encoding='utf8'))
if not assets['complete'] or build['status']!='Succeeded':raise RuntimeError('Production is not complete')
delivery=dict(status='assets_saved_and_native_build_completed',assets=assets['saved'],build=build,
    action='single_action',capacity=5,ammo_group='ammo_127',source_fire_cycle=1.,cock_latch=.60,
    default_fire_interval=catalog['weapon']['base']['fire_interval'],reference='https://www.bilibili.com/video/BV1pj411e7Jw/ 102-104s',
    reference_read=True,editor_started_by_this_task=False,game_started=False,testing='Not performed; user testing',
    saved_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(O/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf8')
(O/'README.md').write_text((P/'Docs/Weapons/rsh12-single-action-20261003.md').read_text(encoding='utf8'),encoding='utf8')
base=P/'Docs/Weapons/rsh12-integration-20261003.md';text=base.read_text(encoding='utf8')
note='\n\n## 单动动作更新\n\nRSH-12 当前已改为每枪右手拇指拨锤的单动模式。新开火与 ADS 动作、源时钟锁定及保存/构建状态见 [单动开火与拨锤](rsh12-single-action-20261003.md)。旧导入配方保留为模型制作来源。\n'
if '## 单动动作更新' not in text:base.write_text(text+note,encoding='utf8')
print('RSH12_SINGLE_ACTION_DELIVERY_SAVED')
