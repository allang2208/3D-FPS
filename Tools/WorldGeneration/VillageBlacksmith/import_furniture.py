"""Import the small furnishing kit and reuse the existing forge's oak/iron materials."""
import json,runpy
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
source=root/'SourceAssets/HillsVillageBlacksmith20261117/Authored'
dest='/Game/WorldGeneration/TemperateHills/VillageBlacksmith'
A,E,L=u.AssetToolsHelpers.get_asset_tools(),u.EditorAssetLibrary,u.MaterialEditingLibrary
def get(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save '+obj.get_path_name())
def material(name):
    path=dest+'/Materials/'+name
    obj=get(path) if E.does_asset_exist(path) else A.create_asset(name,dest+'/Materials',u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(obj)
    return obj
def constant(mat,value,prop):
    node=L.create_material_expression(mat,u.MaterialExpressionConstant);node.r=value
    L.connect_material_property(node,'',getattr(u.MaterialProperty,'MP_'+prop))

mats={'Oak':get('/Game/Props/CastingStation20260926/RealismV5/M_OakDry'),
      'Iron':get('/Game/Props/CastingStation20260926/RealismV5/MI_DarkForgedIron'),
      'Stone':get('/Game/UnrealNormandy/MaterialInstances/MI_StoneWall_Pieces_00B_Gray')}
cloth=material('M_WornLinen')
n=L.create_material_expression(cloth,u.MaterialExpressionCustom)
n.set_editor_property('code','float2 p=UV*260.; float warp=.5+.5*sin(p.x*6.283); float weft=.5+.5*sin(p.y*6.283); return float3(.22,.18,.12)*(.74+.26*max(warp,weft));')
n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
pin=u.CustomInput();pin.set_editor_property('input_name','UV');n.set_editor_property('inputs',[pin])
uv=L.create_material_expression(cloth,u.MaterialExpressionTextureCoordinate)
L.connect_material_expressions(uv,'',n,'UV');L.connect_material_property(n,'',u.MaterialProperty.MP_BASE_COLOR)
constant(cloth,.94,'ROUGHNESS');L.recompile_material(cloth);save(cloth);mats['Linen']=cloth
for label,slot in [('BlacksmithSign','Sign'),('ClosedPlaque','Closed')]:
    task=u.AssetImportTask();task.filename=str(source/('T_'+label+'.png'))
    task.destination_path=dest+'/Textures';task.destination_name='T_'+label
    task.automated=True;task.replace_existing=True;A.import_asset_tasks([task])
    tex=get(task.destination_path+'/'+task.destination_name);tex.srgb=True;tex.max_texture_size=1024;save(tex)
    mat=material('M_'+label);n=L.create_material_expression(mat,u.MaterialExpressionTextureSample)
    n.texture=tex;n.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR
    L.connect_material_property(n,'RGB',u.MaterialProperty.MP_BASE_COLOR)
    constant(mat,.87,'ROUGHNESS');L.recompile_material(mat);save(mat);mats[slot]=mat

saved=[]
for row in json.loads((source/'furniture-manifest.json').read_text(encoding='utf-8')):
    name=row['name'];task=u.AssetImportTask();task.filename=str(source/(name+'.fbx'))
    task.destination_path=dest+'/Meshes';task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False
    options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False
    options.import_as_skeletal=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=True
    data.generate_lightmap_u_vs=False;task.options=options;A.import_asset_tasks([task])
    mesh=get(task.destination_path+'/'+name)
    for i,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name)
        if key not in mats:raise RuntimeError('Unexpected furniture slot '+key)
        mesh.set_material(i,mats[key])
    save(mesh);saved.append(mesh.get_path_name())
runpy.run_path(str(Path(__file__).with_name('save_furniture_usage.py')))
(source.parent/'furniture-saved.json').write_text(json.dumps(dict(saved=saved,runtime_tested=False),indent=2),encoding='utf-8')
