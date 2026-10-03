"""Persist the adopted author parameters beside the original 2011 recipe."""
import json,shutil
from pathlib import Path
from surface_contract import ws_parameters,GRAIN,BODY
O=Path(__file__).parent;P=O.parents[1]
path=P/'SourceAssets/PitViper2011Integration20261002/finish_recipe.json'
before=O/'Before/finish_recipe.json'
if not before.exists():before.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,before)
recipe=json.loads(path.read_text(encoding='utf8'))
for key,spec in recipe['slots'].items():
    values=ws_parameters(BODY+'MI_PitViper2011_'+key.replace('-','_'))
    spec['roughness']=values['Roughness'];spec['surface_scalars']=values
recipe.update(surface_refinement='2011 SurfaceRefine20261003: continuous quiet machining finish',grain_texture=GRAIN)
path.write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf8')
(O/'finish_recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2),encoding='utf8')
print('PIT_VIPER_FINISH_AUTHOR_RECIPE_SAVED',flush=True)
