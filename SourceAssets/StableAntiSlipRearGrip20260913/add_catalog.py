import json
from pathlib import Path
P=Path(__file__).parent
catalog=P.parents[1]/'Content/ColdSteelData/gunsmith.json'
data=json.loads(catalog.read_text(encoding='utf-8-sig'))
option={'id':'stable_antislip_reargrip','name':'稳固防滑后握','description':'实心人体工学后握把，指槽与橡胶防滑面提升握持稳定性。开镜瞄准速度降低10%，后坐力控制提高20%，枪械稳定性提高15%。','effects':[{'text':'开镜瞄准速度降低10%','benefit':-1},{'text':'后坐力控制提高20%','benefit':1},{'text':'枪械稳定性提高15%','benefit':1}],'stats':{'ads_percent':1/0.9-1,'recoil_mult':0.8,'shake_mult':0.85}}
for weapon in data['weapons']:
    if 'reargrip' not in weapon.get('allowed',[]):continue
    options=weapon['options']['reargrip']
    existing=next((i for i,x in enumerate(options) if x['id']==option['id']),None)
    if existing is None:options.append(option)
    else:options[existing]=option
catalog.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
