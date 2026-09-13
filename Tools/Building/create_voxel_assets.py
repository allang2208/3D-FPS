"""Author the project's 20 cm voxel palette. No maps, gameplay runs or screenshots."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'Saved/VoxelFoundation20260913'
OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/Building/Voxels'
EAL=u.EditorAssetLibrary
LIB=u.MaterialEditingLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
EAL.make_directory(DEST)
references=[]

def load(path):
    asset=u.load_asset(path)
    if asset is None: raise RuntimeError('Required source asset missing: '+path)
    references.append(path)
    return asset

def asset(name,cls,factory):
    path=DEST+'/'+name
    return load(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(name,DEST,cls,factory)

def node(mat,cls): return LIB.create_material_expression(mat,cls)
def wire(source,target,pin,output=''): LIB.connect_material_expressions(source,output,target,pin)
def prop(source,name): LIB.connect_material_property(source,'',getattr(u.MaterialProperty,'MP_'+name))
def scalar(mat,name,value):
    result=node(mat,u.MaterialExpressionScalarParameter)
    result.set_editor_property('parameter_name',name)
    result.set_editor_property('default_value',value)
    return result
def custom(mat,code,inputs,size):
    result=node(mat,u.MaterialExpressionCustom)
    result.set_editor_property('code',code)
    result.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    result.set_editor_property('inputs',pins)
    for name,source in inputs.items():wire(source,result,name)
    return result
def save(value):
    if not EAL.save_loaded_asset(value,False):raise RuntimeError('Could not save '+value.get_path_name())
    return value

surfaces={}
for material_id,family in [('wood','WoodSurface_00A'),('stone','StoneSurface_00A')]:
    mat=asset('M_Voxel_'+material_id.title(),u.Material,u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    mat.set_editor_property('tangent_space_normal',False)
    position=node(mat,u.MaterialExpressionWorldPosition)
    normal=node(mat,u.MaterialExpressionVertexNormalWS)
    # Same 80 cm world projection in the standalone cubes and merged chunks.
    uv=custom(mat,'float3 a=abs(N); return (a.z>0.5?P.xy:(a.x>0.5?P.yz:P.xz))/80.0;',{'P':position,'N':normal},2)
    samples={}
    for suffix,sampler in [('BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('RHAOM',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]:
        t=node(mat,u.MaterialExpressionTextureSample)
        t.set_editor_property('texture',load('/Game/UnrealNormandy/Textures/T_'+family+'_'+suffix))
        t.set_editor_property('sampler_type',sampler);wire(uv,t,'UVs');samples[suffix]=t
    wet=node(mat,u.MaterialExpressionCollectionParameter)
    wet.set_editor_property('collection',load('/Game/Weather/Materials/MPC_FPS_Weather'))
    wet.set_editor_property('parameter_name','WeatherWetness')
    color=custom(mat,'float m=0.96+0.04*sin(P.x*.011+sin(P.y*.007)+P.z*.003); return C*m*lerp(1.0,0.72,saturate(Wet));',{'C':samples['BaseColor'],'P':position,'Wet':wet},3)
    detail=custom(mat,'float3 a=abs(N); float3 U=a.x>0.5?float3(0,1,0):float3(1,0,0); float3 V=a.z>0.5?float3(0,1,0):float3(0,0,1); return normalize(T.x*U+T.y*V+T.z*N);',{'T':samples['Normal'],'N':normal},3)
    rough=custom(mat,'return lerp(clamp(M.r,0.48,0.96),0.3,saturate(Wet));',{'M':samples['RHAOM'],'Wet':wet},1)
    prop(color,'BASE_COLOR');prop(detail,'NORMAL');prop(rough,'ROUGHNESS')
    prop(scalar(mat,'Specular',.3),'SPECULAR')
    LIB.recompile_material(mat);surfaces[material_id]=save(mat)

ghost=asset('M_Voxel_Preview',u.Material,u.MaterialFactoryNew())
LIB.delete_all_material_expressions(ghost)
ghost.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
ghost.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
position=node(ghost,u.MaterialExpressionWorldPosition)
normal=node(ghost,u.MaterialExpressionVertexNormalWS)
tint=node(ghost,u.MaterialExpressionVectorParameter)
tint.set_editor_property('parameter_name','Tint');tint.set_editor_property('default_value',u.LinearColor(.2,.7,.48,1))
opacity=custom(ghost,'float3 a=abs(N); float2 uv=(a.z>0.5?P.xy:(a.x>0.5?P.yz:P.xz))/20.0; float2 f=frac(uv); float e=min(min(f.x,1-f.x),min(f.y,1-f.y)); return lerp(0.07,0.6,1-smoothstep(0.015,0.045,e));',{'P':position,'N':normal},1)
prop(tint,'EMISSIVE_COLOR');prop(opacity,'OPACITY');LIB.recompile_material(ghost);save(ghost)

meshes={}
mesh_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for material_id,surface in surfaces.items():
    path=DEST+'/SM_Voxel20_'+material_id.title()
    mesh=load(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset('/Engine/BasicShapes/Cube',path)
    settings=mesh_editor.get_lod_build_settings(mesh,0)
    settings.set_editor_property('build_scale3d',u.Vector(.2,.2,.2))
    mesh_editor.set_lod_build_settings(mesh,0,settings)
    mesh.set_material(0,surface)
    # Generated 20 cm geometry needs a matching simple hull; don't retain the source 1m box.
    mesh_editor.remove_collisions(mesh)
    mesh_editor.add_simple_collisions(mesh,u.ScriptCollisionShapeType.BOX)
    meshes[material_id]=save(mesh)

factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.VoxelBuildPalette)
palette=asset('DA_VoxelBuildPalette',u.VoxelBuildPalette,factory)
entries=[]
for material_id,title in [('wood','木材'),('stone','石头')]:
    entry=u.VoxelBuildMaterial()
    entry.set_editor_property('id',material_id)
    entry.set_editor_property('display_name',u.Text(title))
    entry.set_editor_property('surface',surfaces[material_id])
    entry.set_editor_property('example_mesh',meshes[material_id])
    entries.append(entry)
palette.set_editor_property('materials',entries)
palette.set_editor_property('preview_material',ghost)
save(palette)

# Read the downloaded EBS definitions as integration source material. No EBS
# Character/GameMode is instantiated, changed, or installed as a project default.
ebs={}
for name in ('DT_EBS_Requirements','DT_EBS_BuildingObjects','DT_EBS_BuildingLists'):
    table=load('/Game/EasyBuildingSystem/Blueprints/DataTables/'+name)
    ebs[name]=json.loads(u.DataTableFunctionLibrary.export_data_table_to_json_string(table))
(OUT/'ebs-definitions.json').write_text(json.dumps(ebs,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'authoring.json').write_text(json.dumps({'cell_size_cm':20,'palette':palette.get_path_name(),
    'meshes':{key:value.get_path_name() for key,value in meshes.items()},'source_references':sorted(set(references)),
    'ebs_role':'Imported reference library; runtime editing uses the native voxel world.',
    'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('VOXEL_ASSETS_AUTHORED '+palette.get_path_name())
