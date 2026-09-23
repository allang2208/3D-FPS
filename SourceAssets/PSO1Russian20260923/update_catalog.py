"""Add only the three opt-in PSO entries without reformatting the catalog."""
import json,re
from pathlib import Path
p=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/gunsmith.json')
text=p.read_bytes().decode('utf-8-sig');newline='\r\n' if '\r\n' in text else '\n'
descriptions={
 'ue_akm':'经典侧装镜筒与尖点分划，通过 AKM 专用机匣侧座安装。',
 'ue_a762':'经典侧装镜筒与尖点分划，使用 A762 专用机匣接口和枪钢涂层。',
 'ue_pkm_lowpoly':'经典侧装镜筒与尖点分划，安装于 PKM 后部机匣侧座，随枪体保持固定。'}
for weapon,description in descriptions.items():
    start=text.index('"id": "'+weapon+'"')
    options=text.index('"options":',start)
    match=re.search(r'"optic"\s*:\s*\[',text[options:])
    a=options+match.end()-1
    array,end=json.JSONDecoder().raw_decode(text[a:])
    if any(x['id']=='pso1_4x' for x in array):continue
    entry={'id':'pso1_4x','name':'PSO-1 四倍瞄准镜','description':description,
           'effects':[{'text':'固定四倍瞄准；开镜耗时不变','benefit':0}],'stats':{}}
    encoded=json.dumps(entry,ensure_ascii=False,indent=2).replace('\n',newline)
    encoded=newline.join('        '+line for line in encoded.split(newline))
    end_bracket=a+end-1
    prefix=text[:end_bracket].rstrip()
    text=prefix+','+newline+encoded+newline+'      '+text[end_bracket:]
p.write_bytes(text.encode('utf-8'))
print('PSO1_CATALOG_UPDATED AKM A762 PKM')
