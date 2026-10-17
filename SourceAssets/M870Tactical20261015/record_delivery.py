"""Record completed production receipts; this does not run checks or gameplay."""
from pathlib import Path
from datetime import datetime
import json
O=Path(__file__).parent;P=O.parents[1]
assets=json.loads((O/'import_receipt.json').read_text());build=json.loads((O/'build_receipt.json').read_text(encoding='utf-8-sig'));author=json.loads((O/'authoring.json').read_text())
delivery=dict(definition='ue_m870',name='M870 Tactical',recorded_at=datetime.now().astimezone().isoformat(),assets_saved=assets.get('completed',False),asset_count=len(assets['saved']),editor_build_succeeded=build['succeeded'],build_receipt=str(O/'build_receipt.json'),asset_receipt=str(O/'import_receipt.json'),editable_source=str(O/'M870_Gameplay_Editable.blend'),animation_count=len(author['clips']),assembly_source=str(O/'Assembly/M870_Assembly_Editable.blend'),catalog_icon=str(P/'Content/ColdSteelData/Icons/ue_m870.png'),acquisition=str(O/'acquisition_receipt.json'),runtime_tested=False,auditioned=False,multiplayer_tested=False,entry_points=['one-time warehouse armory grant: one M870 and 42 ammo_12g','gun assembly workbench: assemble_m870'],attachments='factory configuration only',source_note='No native source changed after the successful Editor build; the final revision updates asset authoring and imported packages only.')
(O/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
doc=P/'Docs/Weapons/m870-tactical-20261015.md';text=doc.read_text(encoding='utf-8');text=text.replace('制作枪体、泵动护木、枪机与扳机的机械绑定。','制作枪体、泵动护木、枪机、扳机与装填门的机械绑定。')
old='本页描述制作内容与接入合同。实际资产保存状态由本批 `import_receipt.json` 记录，必要 Editor 构建由 `build_receipt.json` 记录；仅写好制作脚本不能作为资产已保存的证明。最终完成状态另记于 `delivery.json`。'
new='本批已实际保存 **32 份 UE 资产**，包括视模、骨架、13 条动画、纹理／材质、世界模型、6 个工作台网格及 5 份声音。最终编辑器批次 `import_bridge_final.txt` 返回 `success=True` 和 `M870_SAVED 32 assets`，装备外观目录已合并。\n\n`FPSGAMEEditor Win64 Development` 后台构建成功，回执为 `build_receipt.json`，完整输出为 `build_editor.log`；基础构建日志是 `Saved/BuildEditor/build-20261015-225627.log`。之后仅修订和导入本枪资产，没有再修改原生源码。`delivery.json` 记录此次完成范围。\n\n模型与动作源通过后台 Blender 制作。早期批次在后台 commandlet 完成贴图、材质和视模保存；后续检测到已有编辑器运行后，通过既有 MCP 批次互斥完成最终导入。此次没有主动启动或关闭图形编辑器。'
doc.write_text(text.replace(old,new),encoding='utf-8')
print(json.dumps({k:delivery[k] for k in ('assets_saved','asset_count','animation_count','editor_build_succeeded','runtime_tested')},ensure_ascii=False))
