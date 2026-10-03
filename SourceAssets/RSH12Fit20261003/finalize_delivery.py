import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
receipt=json.loads((O/'import_receipt.json').read_text(encoding='utf8'))
if not receipt['complete']:raise RuntimeError('RSH-12 corrected asset import is incomplete')
delivery=dict(status='Corrected geometry and current animation consumers imported and saved',saved_assets=receipt['saved'],
 changes=['Extractor rear plate follows the cylinder and extractor','Front extractor rod split from crane','Right release button and fixed front pieces bound to frame','Five measured chamber centers and bore facets','Cartridge rim seated against rear plane; axial insertion'],
 authored=['Single RSH12 mesh','Dual right and left RSH12 meshes','Standalone source cartridge','Four single-action fire clips','Three current non-fire contact/mechanical profiles'],
 narrow_diagnosis='Original geometry and native shared idle/reload pose calculations; diagnostic Blender closeups',
 full_game_tested=False,cpp_modified=False,cpp_build_required=False,editor_started=False,game_started=False,
 capacity=5,single_action_cycle_preserved=True,prior_assets_backup='BeforeAssets',
 evidence=['geometry_diagnosis.json','part_shells.json','fit_contract.json','pose_fit_diagnosis.json','before_reload_seats.png','after_reload_seats.png','import_receipt.json'])
(O/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf8')
doc=P/'Docs/Weapons/rsh12-cylinder-fit-20261003.md';text=doc.read_text(encoding='utf8')
old='制作和导出已完成；等待当前编辑器 PIE 结束后通过互斥桥导入保存。导入脚本先检查 PIE，发现运行中就退出，未关闭编辑器或结束正在运行的游戏。实际保存状态以 `SourceAssets/RSH12Fit20261003/import_receipt.json` 为准。'
new='制作和导出已完成，三个持枪模型、独立弹药模型、四个单动开火片段及三个当前 profile 共 11 个 UE 资产已实际导入并保存。现有编辑器自行退出后使用后台 commandlet，未关闭编辑器、未结束其他运行现场、未新开编辑器或游戏。保存记录为 `SourceAssets/RSH12Fit20261003/import_receipt.json`，交付记录为同目录 `delivery.json`。游戏内效果由用户测试；本次仅进行用户指定两个问题的源几何与共享姿态排查。'
if old in text:doc.write_text(text.replace(old,new),encoding='utf8')
print('RSH12_FIT_DELIVERED',len(receipt['saved']))
