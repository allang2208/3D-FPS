"""Import new closed scan packages, then change only the two quarry mesh references."""
import json, shutil
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/HillsLandscapeRepair20261117/SolidScansR9'
DEST='/Game/WorldGeneration/TemperateHills/WhiteCliffs'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
records=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
meshes=[];report={'meshes':[]}
cut_path=DEST+'/Materials/M_LimestoneCut'
cut=u.load_asset(cut_path) if E.does_asset_exist(cut_path) else A.create_asset('M_LimestoneCut',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(cut)
cut.set_editor_property('used_with_instanced_static_meshes',True)
def node(cls):return L.create_material_expression(cut,cls)
def connect(a,output,b,pin=''):
    if not L.connect_material_expressions(a,output,b,pin):raise RuntimeError('Cut material pin '+pin)
uv=node(u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',3.);uv.set_editor_property('v_tiling',3.)
base=node(u.MaterialExpressionTextureSample)
base.texture=u.load_asset('/Game/UnrealNormandy/Textures/T_StoneSurface_03A_BaseColor')
base.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR;connect(uv,'',base,'UVs')
mono=node(u.MaterialExpressionDesaturation);fraction=node(u.MaterialExpressionConstant);fraction.r=1.
connect(base,'RGB',mono);connect(fraction,'',mono,'Fraction')
power=node(u.MaterialExpressionPower);power.set_editor_property('const_exponent',.65);connect(mono,'',power,'Base')
L.connect_material_property(power,'',u.MaterialProperty.MP_BASE_COLOR)
normal=node(u.MaterialExpressionTextureSample)
normal.texture=u.load_asset('/Game/UnrealNormandy/Textures/T_StoneSurface_03A_Normal')
normal.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL;connect(uv,'',normal,'UVs')
flat=node(u.MaterialExpressionConstant3Vector);flat.constant=u.LinearColor(0.,0.,1.,1.)
blend=node(u.MaterialExpressionLinearInterpolate);blend.set_editor_property('const_alpha',.45)
connect(flat,'',blend,'A');connect(normal,'RGB',blend,'B');L.connect_material_property(blend,'',u.MaterialProperty.MP_NORMAL)
rough=node(u.MaterialExpressionConstant);rough.r=.85;L.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
L.recompile_material(cut)
if not E.save_loaded_asset(cut,False):raise RuntimeError('Cut material save failed')
report['cut_material']=cut_path
for row,label in zip(records,('CliffA','CliffB')):
    path=DEST+'/Meshes/'+row['name']
    if E.does_asset_exist(path):raise RuntimeError('New revision already exists: '+path)
    task=u.AssetImportTask();task.filename=row['fbx'];task.destination_path=DEST+'/Meshes'
    task.destination_name=row['name'];task.automated=True;task.replace_existing=False;task.save=False
    opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False
    opts.import_as_skeletal=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opts.static_mesh_import_data.combine_meshes=True;opts.static_mesh_import_data.auto_generate_collision=False
    opts.static_mesh_import_data.generate_lightmap_u_vs=False
    opts.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options=opts;A.import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed '+path)
    mat=u.load_asset(DEST+'/Materials/M_'+label)
    mat.modify();mat.set_editor_property('two_sided',False);L.recompile_material(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Material save failed')
    for i,slot in enumerate(mesh.static_materials):
        mesh.set_material(i,cut if str(slot.material_slot_name)=='LimestoneCut' else mat)
    settings=mesh.get_editor_property('nanite_settings');settings.enabled=True
    settings.fallback_percent_triangles=.5;settings.fallback_relative_error=.1
    mesh.set_editor_property('nanite_settings',settings)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    box=mesh.get_bounding_box();size=[box.max.x-box.min.x,box.max.y-box.min.y,box.max.z-box.min.z]
    if any(abs(a-b)>1. for a,b in zip(size,row['size_cm'])):raise RuntimeError('FBX unit mismatch '+str(size))
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed '+path)
    meshes.append(mesh);report['meshes'].append({'path':path,'size_cm':size,
        'materials':[s.material_interface.get_path_name() for s in mesh.static_materials],'saved':True})
data=u.load_asset('/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming')
source=ROOT/'Content/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming.uasset'
shutil.copy2(source,OUT/'DA_TemperateHillsStreaming-before-solid.uasset')
refs=list(data.get_editor_property('white_cliff_meshes'));refs[0]=meshes[0];refs[1]=meshes[1]
data.modify();data.set_editor_property('white_cliff_meshes',refs)
if not E.save_loaded_asset(data,False):raise RuntimeError('Mesh reference save failed')
report['data_asset_saved']=True
(OUT/'saved.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('HILLS_CLOSED_QUARRY_SCANS_SAVED')
