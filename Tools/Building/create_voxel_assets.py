"""Author the project's 20 cm voxel palette. No maps, gameplay runs or screenshots."""
from pathlib import Path
import json
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'Saved/VoxelFoundation20260913'
OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/Building/Voxels/Rounded'
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
    # Blend three world projections through curved normals. A dominant-axis
    # switch made a visible texture seam halfway around each rounded corner.
    scale=scalar(mat,'TextureScaleCm',80)
    weights=custom(mat,'float3 w=pow(abs(normalize(N)),4); return w/max(w.x+w.y+w.z,0.0001);',{'N':normal},3)
    uv={axis:custom(mat,'return P.'+swizzle+'/max(Scale,1.0);',{'P':position,'Scale':scale},2)
        for axis,swizzle in [('X','yz'),('Y','xz'),('Z','xy')]}
    samples={}
    for suffix,sampler in [('BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('RHAOM',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]:
        texture=load('/Game/UnrealNormandy/Textures/T_'+family+'_'+suffix)
        planes={}
        for axis in ('X','Y','Z'):
            t=node(mat,u.MaterialExpressionTextureSample)
            t.set_editor_property('texture',texture);t.set_editor_property('sampler_type',sampler)
            wire(uv[axis],t,'UVs');planes[axis]=t
        samples[suffix]=planes
    def blended(planes):return custom(mat,'return X*W.x+Y*W.y+Z*W.z;',dict(planes,W=weights),3)
    wet=node(mat,u.MaterialExpressionCollectionParameter)
    wet.set_editor_property('collection',load('/Game/Weather/Materials/MPC_FPS_Weather'))
    wet.set_editor_property('parameter_name','WeatherWetness')
    edge=custom(mat,'float3 a=abs(normalize(N)); return saturate((1-max(a.x,max(a.y,a.z)))*3);',{'N':normal},1)
    wear=scalar(mat,'EdgeTone',.025 if material_id=='wood' else .045)
    color=custom(mat,'float m=0.97+0.03*sin(P.x*.011+sin(P.y*.007)+P.z*.003); return C*m*(1+Edge*Wear)*lerp(1.0,0.72,saturate(Wet));',{'C':blended(samples['BaseColor']),'P':position,'Wet':wet,'Edge':edge,'Wear':wear},3)
    strength=scalar(mat,'NormalStrength',.65 if material_id=='wood' else .8)
    detail=custom(mat,'''float3 n=normalize(N);
float3 dx=float3(0,X.x,X.y)/max(X.z,0.2);
float3 dy=float3(Y.x,0,Y.y)/max(Y.z,0.2);
float3 dz=float3(Z.x,Z.y,0)/max(Z.z,0.2);
float3 d=(dx*W.x+dy*W.y+dz*W.z)*Strength;
return normalize(n+d-n*dot(d,n));''',dict(samples['Normal'],N=normal,W=weights,Strength=strength),3)
    rough=custom(mat,'return lerp(clamp(M.r+Edge*.04,0.48,0.96),0.3,saturate(Wet));',{'M':blended(samples['RHAOM']),'Wet':wet,'Edge':edge},1)
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
edge_radius=1.4
rounded=u.VoxelSurfaceLibrary.create_example_mesh(edge_radius)
for material_id,surface in surfaces.items():
    path=DEST+'/SM_Voxel20_'+material_id.title()
    mesh=load(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset('/Engine/BasicShapes/Cube',path)
    settings=mesh_editor.get_lod_build_settings(mesh,0)
    settings.set_editor_property('build_scale3d',u.Vector(1,1,1))
    mesh_editor.set_lod_build_settings(mesh,0,settings)
    options=u.GeometryScriptCopyMeshToAssetOptions()
    options.set_editor_property('enable_recompute_normals',False)
    options.set_editor_property('enable_recompute_tangents',True)
    options.set_editor_property('replace_materials',True)
    options.set_editor_property('new_materials',[surface])
    options.set_editor_property('use_build_scale',False)
    _,outcome=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(rounded,mesh,options,u.GeometryScriptMeshWriteLOD())
    if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Could not author rounded block '+path)
    mesh.set_material(0,surface)
    # Keep a 20 cm box collider; runtime selection uses the same unrounded grid.
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
palette.set_editor_property('edge_radius_cm',edge_radius)
save(palette)

# Read the downloaded EBS definitions as integration source material. No EBS
# Character/GameMode is instantiated, changed, or installed as a project default.
ebs={}
for name in ('DT_EBS_Requirements','DT_EBS_BuildingObjects','DT_EBS_BuildingLists'):
    table=load('/Game/EasyBuildingSystem/Blueprints/DataTables/'+name)
    ebs[name]=json.loads(u.DataTableFunctionLibrary.export_data_table_to_json_string(table))
(OUT/'ebs-definitions.json').write_text(json.dumps(ebs,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'authoring.json').write_text(json.dumps({'cell_size_cm':20,'edge_radius_cm':edge_radius,'surface':'Rounded union with blended world projections','palette':palette.get_path_name(),
    'meshes':{key:value.get_path_name() for key,value in meshes.items()},'source_references':sorted(set(references)),
    'ebs_role':'Imported reference library; runtime editing uses the native voxel world.',
    'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
u.log('VOXEL_ASSETS_AUTHORED '+palette.get_path_name())
