"""Rebuild only the two misassigned HK416 material graphs and record saved bindings."""
import unreal as u,ast,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'HK416Reworked20260930';P=O.parents[1]
ROOT='/Game/Weapons/HK416/Reworked20260930'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
auth=json.loads((S/'authoring.json').read_text())
auth['material_groups']={key:auth['material_groups'][key] for key in ('M_HK416_Laser_Grip','M_HK416_Flash_Light')}
report={'saved':[],'materials':{},'before':{},'after':{},'static_bindings':{},'runtime_tested':False}
recipe=ast.parse((S/'import_assets.py').read_text())
exec(compile(ast.Module(body=[n for n in recipe.body if isinstance(n,ast.FunctionDef) and n.name in ('record','load','save','create')],type_ignores=[]),'HK416 material save helpers','exec'),globals())
def create(name,folder,cls,factory):
    existing=u.load_asset(folder+'/'+name)
    return existing if existing else A.create_asset(name,folder,cls,factory)
for name in auth['material_groups']:
    mat=load(ROOT+'/Materials/'+name)
    report['before'][name]=[node.texture.get_path_name() for node in L.get_material_expressions(mat) if isinstance(node,u.MaterialExpressionTextureSample) and node.texture]
record()
tree=ast.parse((P/'Tools/Weather/build_natural_weather.py').read_text(encoding='utf8'))
helpers={'unreal':u,'LIB':L};wanted={'node','wire','prop','scalar','constant','vector','custom'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted],type_ignores=[]),'HK416 material helpers','exec'),helpers)
node,custom,prop,scalar,constant,vector=[helpers[k] for k in ('node','custom','prop','scalar','constant','vector')]
textures={file.stem:load(ROOT+'/Textures/T_HK416_'+file.stem) for file in (S/'Original/textures').iterdir() if file.is_file()}
materials={};wetmap={}
material_loop=next(n for n in recipe.body if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [t.id for t in n.target.elts]==['name','group'])
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    material_loop.body=[n for n in material_loop.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='set_metadata_tag')]
exec(compile(ast.Module(body=[material_loop],type_ignores=[]),'HK416 two material rebuild','exec'),globals())
for name,mat in materials.items():
    samples=[]
    for expr in L.get_material_expressions(mat):
        if isinstance(expr,u.MaterialExpressionTextureSample) and expr.texture:
            tex=expr.texture;samples.append({'asset':tex.get_path_name(),'sampler':str(expr.sampler_type),'srgb':tex.srgb,'compression':str(tex.compression_settings),'normal_flip_green':tex.flip_green_channel})
    report['after'][name]=samples
    expected=auth['material_groups'][name]
    if any('T_HK416_'+expected+'_' not in row['asset'] for row in samples):raise RuntimeError('Unexpected atlas still present in '+name)
for part in ('vertical','flashlight','laser'):
    mesh=load(ROOT+'/Attachments/SM_HK416_'+part)
    report['static_bindings'][part]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.static_materials]
report['complete']=True;record();print('HK416_TWO_ATLAS_MATERIALS_CORRECTED_AND_SAVED',flush=True)
