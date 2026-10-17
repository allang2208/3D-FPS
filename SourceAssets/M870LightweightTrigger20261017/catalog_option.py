"""M870-only numeric trigger kit; preserve the accepted native trigger geometry."""
from copy import deepcopy

FACTORY={'id':'false','name':'原厂扳机套件',
         'description':'M870 原厂扳机组件。','effects':[],'stats':{}}
OPTION={'id':'m870_lightweight_trigger_kit','name':'轻量化扳机套件',
        'description':'M870 专用的轻量化扳机组件，保留原厂扳机外形与安装接口。',
        'effects':[{'text':'射击间隔减少25%','benefit':1},
                   {'text':'后坐力减少5%','benefit':1},
                   {'text':'枪械稳定性提升5%','benefit':1}],
        'stats':{'fire_interval_mult':.75,'recoil_mult':.95,'stability_mult':1.05}}

def merge(weapon):
    if weapon['id']!='ue_m870':raise ValueError('This kit is exclusive to M870')
    if 'trigger' not in weapon['allowed']:
        index=weapon['allowed'].index('muzzle')+1 if 'muzzle' in weapon['allowed'] else len(weapon['allowed'])
        weapon['allowed'].insert(index,'trigger')
    rows=weapon['options'].get('trigger',[])
    weapon['options']['trigger']=[deepcopy(FACTORY)]+[
        deepcopy(row) for row in rows if row['id'] not in ('false',OPTION['id'])]+[deepcopy(OPTION)]
