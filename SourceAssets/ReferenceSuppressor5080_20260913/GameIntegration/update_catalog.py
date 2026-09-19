"""Install two distinct muzzle options in the existing four-weapon catalog."""
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME')
path = ROOT/'Content/ColdSteelData/gunsmith.json'
original = path.read_bytes()
catalog = json.loads(original)
updated = []
for weapon in catalog['weapons']:
    options = weapon['options'].get('muzzle', [])
    standard = next((o for o in options if o['id'] == 'true'), None)
    if standard is None:
        continue
    standard.update(
        name='消音器',
        description='降低枪声与枪口火光；后坐力降低10%，枪械稳定性增加10%，子弹速度降低15%。',
        effects=[{'text':text,'benefit':benefit} for text,benefit in [
            ('后坐力降低10%',1),('枪械稳定性增加10%',1),('子弹速度降低15%',-1)]],
        stats={'recoil_mult':.9,'stability_mult':1.1,'bullet_speed_mult':.85})
    tactical = {
        'id':'tactical_suppressor', 'name':'战术消音器',
        'description':'精细斜纹战术消音器，降低枪声与枪口火光；后坐力降低25%，枪械稳定性增加25%，子弹速度降低20%，ADS瞄准速度降低5%。',
        'effects':[{'text':text,'benefit':benefit} for text,benefit in [
            ('后坐力降低25%',1),('枪械稳定性增加25%',1),('子弹速度降低20%',-1),('ADS瞄准速度降低5%',-1)]],
        'stats':{'recoil_mult':.75,'stability_mult':1.25,'bullet_speed_mult':.8,'ads_percent':1/.95-1}}
    existing = next((i for i,o in enumerate(options) if o['id']=='tactical_suppressor'), None)
    if existing is None:
        options.insert(options.index(standard)+1,tactical)
    else:
        options[existing] = tactical
    updated.append(weapon['id'])
if path.read_bytes() != original:
    raise RuntimeError('Catalog changed during this scoped edit; rerun using the current file.')
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('MUZZLE_CATALOG_UPDATED',updated,flush=True)
