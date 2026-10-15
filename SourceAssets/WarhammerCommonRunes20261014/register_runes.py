"""Reuse the live sword rune column; do not duplicate its numbers or icon files."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData'
path=DATA/'warhammer-gunsmith.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
column=next(c for c in data['columns'] if c['key']=='rune')
column.update(options_library='melee-gunsmith.json',options_column='blade_2')
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=DATA/'warhammer-modules.json';data=json.loads(path.read_text(encoding='utf-8-sig'))
for key,appearance in {'haste_rune':'疾风折纹 · 黄色流光','resonance_rune':'共鸣环印 · 青绿呼吸微光',
    'erosion_rune':'侵蚀裂纹 · 紫色渐隐','conduction_rune':'导魔回路 · 蓝色流光'}.items():
    data['slots']['rune'][key]={'appearance':appearance}
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('WARHAMMER_COMMON_RUNES_REGISTERED')
