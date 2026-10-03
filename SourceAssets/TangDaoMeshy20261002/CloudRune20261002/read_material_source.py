"""Read the current blade shader as authoring input; do not modify live assets."""
from pathlib import Path
import json,unreal as u
P=Path(__file__).resolve().parent
paths=[
'/Game/Weapons/TangDao20261002/SurfaceV2/Materials/M_TangDaoBladeRuneSurface',
'/Game/Weapons/TangDao20261002/YanlingBlade20261002/Materials/M_TangDaoBladeRuneSurface_Yanling',
'/Game/Weapons/TangDao20261002/TengyunBlade20261002/Materials/M_TangDaoBladeRuneSurface_Tengyun']
rows=[]
for path in paths:
    material=u.load_asset(path)
    if not material:raise RuntimeError('Missing current TangDao material '+path)
    nodes=list(u.MaterialEditingLibrary.get_material_expressions(material))
    rows.append({'path':material.get_path_name(),
       'custom':[{'name':n.get_name(),'code':n.get_editor_property('code'),
                  'inputs':[str(x.get_editor_property('input_name')) for x in n.get_editor_property('inputs')]}
                 for n in nodes if isinstance(n,u.MaterialExpressionCustom)],
       'scalars':{str(n.get_editor_property('parameter_name')):n.get_editor_property('default_value') for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter)},
       'textures':[{'name':n.get_name(),'sampler':str(n.get_editor_property('sampler_type')),'texture':n.get_editor_property('texture').get_path_name() if n.get_editor_property('texture') else None} for n in nodes if isinstance(n,u.MaterialExpressionTextureObjectParameter)]})
(P/'material_sources.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('CLOUD_RUNE_AUTHORING_SOURCES_READ '+str(len(rows)),flush=True)
