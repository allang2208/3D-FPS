"""Publish only the VIP geometry description; preserve all numeric modifiers."""
import ast,copy,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];OLD=O.parent/'PitViper2011VipGrip20261002'
tree=ast.parse((OLD/'publish_catalog.py').read_text(encoding='utf8'))
option=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='OPTION' for t in n.targets))
description=next(ast.literal_eval(value) for key,value in zip(option.keys,option.values) if ast.literal_eval(key)=='description')
path=P/'Content/ColdSteelData/gunsmith.json';text=path.read_text(encoding='utf-8-sig');catalog=json.loads(text)
weapon=copy.deepcopy(next(w for w in catalog['weapons'] if w['id']=='ue_pit_viper2011'))
for options in (weapon['options']['reargrip'],weapon['pistol_grip_surface']['exclusive_options']):
    for item in options:
        if item['id']=='pit_viper_vip_scales':item['description']=description
backup=O/'Before/Content/ColdSteelData/gunsmith.json'
if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup)
pos=text.index(json.dumps(weapon['id']),text.index('"weapons"'));start=text.rfind('{',0,pos)
_,size=json.JSONDecoder().raw_decode(text[start:])
result=text[:start]+json.dumps(weapon,ensure_ascii=False,indent=2)+text[start+size:]
if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Preserve concurrent catalog publication')
path.write_text(result,encoding='utf8')
record_path=OLD/'catalog.json';record=json.loads(record_path.read_text(encoding='utf8'))
record['option']['description']=description;record['geometry_revision']='longitudinal_grip_20261003'
record_path.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
surface=O.parent/'PitViper2011SurfaceRefine20261003/texture_recipe.json'
record=json.loads(surface.read_text(encoding='utf8'));record['textures']['Vip']=json.loads((O/'texture_recipe.json').read_text(encoding='utf8'))['private']
record['vip_surface_revision']='longitudinal_grip_20261003'
surface.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print('VIP_LONGITUDINAL_DESCRIPTION_PUBLISHED_NUMERIC_STATS_PRESERVED',flush=True)
