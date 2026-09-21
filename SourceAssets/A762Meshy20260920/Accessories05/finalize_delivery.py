from pathlib import Path
import json
O=Path(__file__).parent
g=json.loads((O/'geometry_import.json').read_text());a=json.loads((O/'animations_import.json').read_text())
native=max(O.glob('native_compile_*.txt'),key=lambda p:p.stat().st_mtime)
receipt=native.read_text(encoding='utf-8-sig')
no_changes='Result: NoChanges' in receipt
compiled='Result: Success' in receipt or no_changes
build=('Live Coding returned NoChanges; current source has no pending compile actions' if no_changes else 'Live Coding succeeded; base Editor DLL not rebuilt by this task') if compiled else 'Final native update pending: see '+native.name
out={'asset':'A762','revision':'Accessories05','status':g['status'],'mesh_assets':g['meshes'],'animation_assets':a,
 'editable_source':'A762_AccessoryReady_Editable.blend','runtime_mesh':'/Game/Weapons/A762/Integrated20260920/SK_A762_Manny',
 'native_build':build,'native_receipt':native.name,
 'catalog':'Content/ColdSteelData/gunsmith.json','damage_formula':'Content/ColdSteelData/combat-weapon-formulas.json',
 'balance':{'rpm':900,'akm_damage_coefficients':.95,'akm_recoil':.75,'akm_base_stability':1.25},
 'audio':'Existing AKM audio routes retained','tested':False,'rendered':False,'acceptance':'User testing pending'}
(O/'DELIVERY.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
path=O.parent/'DELIVERY.json';root=json.loads(path.read_text(encoding='utf-8'))
root['integration_editable_source']='Accessories05/A762_AccessoryReady_Editable.blend';root['latest_refinement']='Accessories05/DELIVERY.json';root['build_result']=build;root['accessory_delivery']='Accessories05/DELIVERY.json'
path.write_text(json.dumps(root,ensure_ascii=False,indent=2),encoding='utf-8')
path=O.parent/'README.md';text=path.read_text(encoding='utf-8')
heading='\n\n## 通用配件接入（Accessories05）'
if heading in text:text=text.split(heading)[0]
state=('已完成导入保存；最终编译返回 NoChanges，当前源码无待编译项' if no_changes else '已完成导入保存与 Live Coding') if compiled else '已完成导入保存；最终编译待完成，原因见 '+native.name
text+=heading+'\n\n在用户认可的 Refinement04 基础上接入七类外观配件及现有通用枪管数值选项，拆分机瞄固定底座和可折叠上部，按导轨调整瞄具与 ADS。攻击及强化系数为 AKM 的 95%，基础后坐力为 75%，稳定性为 125%，射速 900 发／分钟。详见 Accessories05/README.md 和 DELIVERY.json；'+state+'，未进行游戏测试。\n'
path.write_text(text,encoding='utf-8')
path=O/'README.md';text=path.read_text(encoding='utf-8')
import re
text=re.sub(r'必要编译结果：native_compile_\d+\.txt', '必要编译结果：'+native.name, text)
path.write_text(text,encoding='utf-8')
print('A762_ACCESSORIES05_DELIVERY_WRITTEN')
