"""Read the current ocean/cloud dependencies needed for authoring; no runtime tests."""
import json
from pathlib import Path
import unreal as u
L=u.MaterialEditingLibrary
out={}
for path in ['/Game/Clearwater/MI_ClearwaterWater','/Game/Weather/Materials/MI_FPSLayeredClouds']:
    m=u.load_asset(path)
    out[path]={'parent':m.get_editor_property('parent').get_path_name(),
        'scalar':str(m.get_editor_property('scalar_parameter_values')),
        'vector':str(m.get_editor_property('vector_parameter_values')),
        'texture':str(m.get_editor_property('texture_parameter_values'))}
m=u.load_asset('/Game/Weather/Materials/M_FPSLayeredClouds')
nodes=list(L.get_material_expressions(m)); rows=[]
for n in nodes:
    row={'name':n.get_name(),'type':n.get_class().get_name(),'desc':str(n.get_editor_property('desc'))}
    if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)):
        row.update(parameter=str(n.get_editor_property('parameter_name')),default=str(n.get_editor_property('default_value')))
    row['inputs']=[x.get_name() if x else None for x in L.get_inputs_for_material_expression(m,n)]
    if isinstance(n,u.MaterialExpressionCustom):row['code']=n.get_editor_property('code')
    rows.append(row)
out['cloud_graph']=rows
e=u.get_editor_subsystem(u.UnrealEditorSubsystem)
out['world']=str(e.get_editor_world());out['game_world']=str(e.get_game_world())
out['cloud_actors']=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    c=a.get_components_by_class(u.VolumetricCloudComponent)
    if c:out['cloud_actors'].append({'actor':a.get_path_name(),'label':a.get_actor_label(),'tags':[str(t) for t in a.tags],'material':c[0].get_material().get_path_name()})
Path(__file__).with_name('Receipts').joinpath('ocean-dependencies.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in out.items() if k!='cloud_graph'}))
