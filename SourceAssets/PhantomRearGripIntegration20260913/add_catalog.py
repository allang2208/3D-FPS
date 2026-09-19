import json
from pathlib import Path
path=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/gunsmith.json')
catalog=json.loads(path.read_text(encoding='utf-8-sig'))
factory={'id':'false','name':'原厂后握把','description':'拆下幻影后握把，恢复这把枪的原厂后握把。','effects':[],'stats':{}}
part={'id':'phantom_reargrip','name':'幻影后握把','description':'镂空框架后握把，带横向防滑纹理。降低开镜速度、提高后坐力控制，但增加腰射随机散布。','effects':[{'text':'ADS瞄准速度降低15%','benefit':-1},{'text':'后坐力控制提高10%','benefit':1},{'text':'腰射随机散布增加10%','benefit':-1}],
      # The existing catalog expresses ADS changes as duration deltas.
      'stats':{'ads_percent':1/0.85-1,'recoil_mult':0.9,'hip_spread_mult':1.1}}
for weapon in catalog['weapons']:
    if weapon['id'] not in ['ue_m4a1','ue_akm','ue_qbz191']:continue
    if 'reargrip' not in weapon['allowed']:weapon['allowed'].append('reargrip')
    options=weapon['options'].setdefault('reargrip',[])
    for value in [factory,part]:
        index=next((i for i,x in enumerate(options) if x['id']==value['id']),None)
        if index is None:options.append(value)
        else:options[index]=value
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
