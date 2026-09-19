"""Register existing generic foregrip IDs on ASH without touching other weapons."""
import json,copy
from pathlib import Path
root=Path(__file__).parents[2];p=root/'Content/ColdSteelData/gunsmith.json'
text=p.read_text(encoding='utf-8-sig');catalog=json.loads(text)
m4=next(w for w in catalog['weapons'] if w['id']=='ue_m4a1')
marker=text.index('"id": "ue_ash12"');start=text.rfind('{',0,marker)
ash,length=json.JSONDecoder().raw_decode(text[start:])
if 'underbarrel' not in ash['allowed']:ash['allowed'].append('underbarrel')
ash['options']['underbarrel']=copy.deepcopy(m4['options']['underbarrel'])
descriptions={
 'false':'恢复 ASH-12 原厂护木支撑姿势。',
 'vertical_foregrip':'直筒式通用前握把，使用适配 ASH 下导轨的夹座与环握手型。',
 'canted_foregrip':'向左下侧倾的通用前握把，采用 ASH 导轨夹座与专用支撑姿势。',
 'prism_handstop':'棱面短阻手器，聚合物握持面搭配与 ASH 枪身一致的金属夹座。',
 'angled_foregrip':'紧凑镂空通用前握把，保留穿孔抓握与防滑区，金属框架匹配 ASH 涂层。'}
for option in ash['options']['underbarrel']:option['description']=descriptions[option['id']]
indent=len(text[:start].rsplit('\n',1)[-1]);replacement=json.dumps(ash,ensure_ascii=False,indent=2).replace('\n','\n'+' '*indent)
p.write_text(text[:start]+replacement+text[start+length:],encoding='utf-8')
print('ASH_UNDERBARREL_CATALOG_INSTALLED')
