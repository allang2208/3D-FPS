"""Import fitted Fab derivatives into new dungeon-only packages; preserve source packs."""
import unreal as u,json,re
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRuinEarthwork20260921')
OUT='/Game/Dungeons/AtmosphereV2/RoomInteriors/Earthwork'
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
receipt={'materials':{},'meshes':{},'source_maps_reused':True,'tests_run':False,'screenshots_taken':False}
receipt_path=ROOT/'Receipts/asset-import.json'

def write():receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Required source unavailable '+path)
    return obj
def node(mat,cls):return L.create_material_expression(mat,cls)
def wire(a,b,pin,out=''):
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
def output(a,prop,pin=''):
    if not L.connect_material_property(a,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Cannot connect output '+prop)
def scalar(mat,value):
    n=node(mat,u.MaterialExpressionConstant);n.r=value;return n
def vector(mat,name,value):
    n=node(mat,u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*value,1));return n
def multiply(mat,a,b):
    n=node(mat,u.MaterialExpressionMultiply);wire(a,n,'A');wire(b,n,'B');return n
def sample(mat,path,name,kind,uv=None):
    tex=load(path);n=node(mat,u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',name);n.texture=tex
    spelling='SAMPLERTYPE'+('VIRTUAL' if tex.virtual_texture_streaming else '')+kind
    member=next(key for key in dir(u.MaterialSamplerType) if key.replace('_','')==spelling)
    n.sampler_type=getattr(u.MaterialSamplerType,member)
    if uv:wire(uv,n,'UVs')
    return n

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Gameplay active; keep current play intact')
for name,recipe in manifest['materials'].items():
    instance_path=OUT+'/Materials/MI_Earth_'+name
    instance=u.load_asset(instance_path)
    if not instance:
        if recipe.get('native_parent'):
            parent=load(recipe['native_parent'])
        else:
            material_path=OUT+'/Materials/M_Earth_'+name;parent=u.load_asset(material_path)
            if not parent:
                parent=A.create_asset('M_Earth_'+name,OUT+'/Materials',u.Material,u.MaterialFactoryNew())
                base=sample(parent,recipe['textures']['base'],'BaseColor','COLOR')
                normal=sample(parent,recipe['textures']['normal'],'Normal','NORMAL')
                color=multiply(parent,base,vector(parent,'Tint',recipe['tint']))
                mask=None
                if recipe['textures'].get('mask'):mask=sample(parent,recipe['textures']['mask'],'SurfaceMasks','MASKS')
                rough=node(parent,u.MaterialExpressionClamp)
                rough.set_editor_property('min_default',recipe['roughness_min']);rough.set_editor_property('max_default',recipe['roughness_max'])
                if recipe['roughness_channel']=='base_alpha':wire(base,rough,'','A')
                else:wire(mask,rough,'','G' if recipe['roughness_channel']=='orm_green' else 'R')
                if name in ('Ridge','Gravel'):
                    uv=node(parent,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('coordinate_index',1)
                    soil=sample(parent,manifest['materials']['Soil']['textures']['base'],'ContactSoil','COLOR',uv)
                    soil_color=multiply(parent,soil,vector(parent,'ContactSoilTint',manifest['materials']['Soil']['tint']))
                    blend=node(parent,u.MaterialExpressionLinearInterpolate);wire(color,blend,'A');wire(soil_color,blend,'B')
                    vc=node(parent,u.MaterialExpressionVertexColor);wire(vc,blend,'Alpha','R');color=blend
                output(color,'BASE_COLOR');output(normal,'NORMAL');output(rough,'ROUGHNESS')
                output(scalar(parent,0),'METALLIC');output(scalar(parent,.24),'SPECULAR')
                if mask:
                    ao=node(parent,u.MaterialExpressionClamp);ao.set_editor_property('min_default',.42);ao.set_editor_property('max_default',1)
                    wire(mask,ao,'','R' if recipe['roughness_channel']=='orm_green' else 'B');output(ao,'AMBIENT_OCCLUSION')
                L.layout_material_expressions(parent);L.recompile_material(parent);save(parent)
        instance=A.create_asset('MI_Earth_'+name,OUT+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        L.set_material_instance_parent(instance,parent)
    if recipe.get('tint'):L.set_material_instance_vector_parameter_value(instance,'Tint',u.LinearColor(*recipe['tint'],1))
    for key,value in recipe.get('scalar_overrides',{}).items():L.set_material_instance_scalar_parameter_value(instance,key,value)
    for key,value in recipe.get('vector_overrides',{}).items():L.set_material_instance_vector_parameter_value(instance,key,u.LinearColor(*value))
    L.update_material_instance(instance);save(instance)
    receipt['materials']['Earth_'+name]=instance.get_path_name();write()

for entry in manifest['objects']:
    path=OUT+'/Meshes/'+entry['name'];mesh=u.load_asset(path)
    if not mesh:
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=OUT+'/Meshes';task.destination_name=entry['name']
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.generate_lightmap_u_vs=False;data.auto_generate_collision=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opts;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=load(path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        if key not in receipt['materials']:raise RuntimeError('Unexpected fitted material slot '+key)
        mesh.set_material(i,load(receipt['materials'][key]))
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=True;mesh.set_editor_property('nanite_settings',settings)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    save(mesh);receipt['meshes'][entry['name']]=mesh.get_path_name();write()
receipt['stage']='assets_saved';write()
print('EARTHWORK_ASSETS_SAVED',len(receipt['meshes']),len(receipt['materials']))
