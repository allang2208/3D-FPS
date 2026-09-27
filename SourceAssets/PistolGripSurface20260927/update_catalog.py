"""Publish only shared grip-treatment options and M1911 host opt-in."""
import json
from pathlib import Path
O=Path(__file__).parent;p=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
text=p.read_text(encoding='utf-8-sig');data=json.loads(text)
options=[
 {'id':'false','name':'原厂纹理','description':'保留原厂握把表面。','effects':[],'stats':{}},
 {'id':'pistol_grip_granular','name':'细颗粒防滑纹','description':'密集细颗粒贴合握把接触面，强调持续握持的稳定。',
  'effects':[{'text':'枪械稳定性增加15%','benefit':1}],'stats':{'stability_mult':1.15}},
 {'id':'pistol_grip_diamond','name':'橡胶菱形防滑纹','description':'柔性橡胶与浅菱形纹理，兼顾握持稳定和后坐控制。',
  'effects':[{'text':'后坐力减少5%','benefit':1},{'text':'枪械稳定性增加5%','benefit':1}],'stats':{'recoil_mult':.95,'stability_mult':1.05}},
 {'id':'pistol_grip_quickdot','name':'细点快握防滑纹','description':'低凸细点表面便于快速调整握姿，以稳定性和后坐控制换取更快开镜。',
  'effects':[{'text':'开镜耗时减少10%','benefit':1},{'text':'枪械稳定性降低5%','benefit':-1},{'text':'后坐力增加5%','benefit':-1}],
  'stats':{'ads_percent':-.10,'stability_mult':.95,'recoil_mult':1.05}}]
weapon=next(w for w in data['weapons'] if w['id']=='ue_m1911')
weapon['pistol_grip_surface']={'mesh':'/Game/Weapons/PistolGripSurface20260927/M1911/SM_M1911_GripSurface','bone':'WPN_root'}
if 'reargrip' not in weapon['allowed']:weapon['allowed'].append('reargrip')
for trait in weapon.get('traits',[]):
    if trait.get('icon')=='neutral' and '改造' in trait.get('text',''):
        trait['text']='瞄具、枪口、弹匣、扳机、握把防滑纹与战术挂件全部可改造'
idpos=text.index('"id": "ue_m1911"');start=text.rfind('{',0,idpos)
_,length=json.JSONDecoder().raw_decode(text[start:]);end=start+length
backup=O/'catalog_before_m1911.json'
if not backup.exists():backup.write_text(text[start:end],encoding='utf-8')
lines=json.dumps(weapon,ensure_ascii=False,indent=2).splitlines();replacement=lines[0]+'\n'+'\n'.join('    '+line for line in lines[1:])
updated=text[:start]+replacement+text[end:]
key='pistol_grip_surface_options';encoded=json.dumps(options,ensure_ascii=False,indent=2)
encoded=encoded.replace('\n','\n  ')
if key in data:
    pos=updated.index('"'+key+'"');vstart=updated.index('[',pos)
    _,length=json.JSONDecoder().raw_decode(updated[vstart:]);updated=updated[:vstart]+encoded+updated[vstart+length:]
else:
    pos=updated.index('{')+1;updated=updated[:pos]+'\n  "'+key+'": '+encoded+','+updated[pos:]
if p.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Catalog changed while preparing scoped grip edit')
p.write_text(updated,encoding='utf-8')
(O/'catalog_change.json').write_text(json.dumps({'host':'ue_m1911','slot':'reargrip','shared_options':options,
 'compatibility':'Explicit fitted mesh opt-in per non-revolver pistol; DW715 unchanged','game_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('PISTOL_GRIP_CATALOG_SAVED',flush=True)
