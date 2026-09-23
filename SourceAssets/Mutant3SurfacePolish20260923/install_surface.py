"""Install Mutant3 surface detail and explicit mesh normals; save only owned assets.
Run with UnrealEditor-Cmd when the editor is closed. No gameplay or preview.
"""
import json
import os
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
DEST = '/Game/Monsters/Mutant3Meshy/SurfacePolish'
MESH = '/Game/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw'
MASTER = '/Game/Monsters/Shared/InfectedSurfaceV1/M_InfectedSurface_V1'
OLD_TEXTURES = '/Game/Monsters/Mutant3Meshy/StyleV1/Textures/T_StyleV1_mutant_Mesh0_0_'
LIB = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary
SUB = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
TOOLS = u.AssetToolsHelpers.get_asset_tools()
TEXTURE_SIZES = {'BaseColor':2048, 'Normal':2048, 'ORM':1024, 'TissueMasks':1024}
REPORT = ROOT/'installation.json'
state = {'state':'started', 'saved':[], 'textures':{}, 'mesh':MESH,
         'game_started':False, 'preview_rendered':False, 'runtime_tested':False}
RESUME_TEXTURES = os.environ.get('MUTANT3_RESUME_TEXTURES') == '1'
if RESUME_TEXTURES:
    state = json.loads(REPORT.read_text(encoding='utf-8'))

def record():
    REPORT.write_text(json.dumps(state,ensure_ascii=False,indent=2,default=str),encoding='utf-8')

def load(path):
    asset = u.load_asset(path)
    if not asset: raise RuntimeError('Required asset missing: '+path)
    return asset

def backup(path):
    relative = Path(path.removeprefix('/Game/'))
    for suffix in ['.uasset','.uexp','.ubulk']:
        source = PROJECT/'Content'/relative.with_suffix(suffix)
        dest = ROOT/'before_content'/relative.with_suffix(suffix)
        if source.exists() and not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,dest)

def save(asset):
    if not LIB.save_loaded_asset(asset,False): raise RuntimeError('Save failed: '+asset.get_path_name())
    state['saved'].append(asset.get_path_name())
    record()

def uv_info(mesh):
    info = mesh.get_editor_property('materials')[0].get_editor_property('uv_channel_data')
    values = {}
    for key in ['initialized','override_densities','local_uv_densities']:
        try: values[key] = info.get_editor_property(key)
        except Exception as exc: values[key] = str(exc)
    return values

targets = [MESH,DEST+'/MI_Mutant3_SurfacePolish']
targets += [DEST+'/Textures/T_Mutant3Surface_'+key for key in TEXTURE_SIZES]
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts = dirty.intersection(targets)
if conflicts: raise RuntimeError('Preserving unsaved target packages: '+str(conflicts))
for target in targets: backup(target)
mesh = load(MESH)
skeleton = mesh.get_editor_property('skeleton')
physics = mesh.get_editor_property('physics_asset')
slots = list(mesh.get_editor_property('materials'))
state['before'] = {'uv_density':uv_info(mesh),
    'build_settings':str(SUB.get_lod_build_settings(mesh,0)),
    'material':slots[0].material_interface.get_path_name(),
    'skeleton':skeleton.get_path_name(),'physics':physics.get_path_name() if physics else None}
record()

master = load(MASTER)
textures = {}
for semantic, cap in TEXTURE_SIZES.items():
    asset_path = DEST+'/Textures/T_Mutant3Surface_'+semantic
    if RESUME_TEXTURES:
        textures[semantic]=load(asset_path)
        state['textures'][semantic]={'asset':asset_path,'max_resolution':cap,'source':OLD_TEXTURES+semantic}
        continue
    tex = u.load_asset(asset_path) or LIB.duplicate_asset(OLD_TEXTURES+semantic,asset_path)
    if not tex: raise RuntimeError('Cannot duplicate texture: '+semantic)
    tex.set_editor_property('max_texture_size',cap)
    tex.set_editor_property('lod_bias',0)
    tex.set_editor_property('never_stream',False)
    tex.set_editor_property('global_force_mip_levels_to_be_resident',False)
    tex.set_editor_property('virtual_texture_streaming',False)
    tex.set_editor_property('srgb',semantic=='BaseColor')
    tex.set_editor_property('filter',u.TextureFilter.TF_DEFAULT)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SHARPEN1
        if semantic=='BaseColor' else u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP
        if semantic=='Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
    if semantic=='Normal':
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel',False)  # Style V1 is already DirectX.
    elif semantic in ['ORM','TissueMasks']:
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    else:
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT)
    LIB.set_metadata_tag(tex,'Mutant3.SurfaceRevision','SurfacePolish20260923')
    LIB.set_metadata_tag(tex,'Mutant3.DetailSource',OLD_TEXTURES+semantic)
    save(tex)
    textures[semantic]=tex
    state['textures'][semantic]={'asset':asset_path,'max_resolution':cap,'source':OLD_TEXTURES+semantic}

name='MI_Mutant3_SurfacePolish'
instance=u.load_asset(DEST+'/'+name) or TOOLS.create_asset(name,DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
MEL.set_material_instance_parent(instance,master)
for semantic,tex in textures.items():
    # UE 5.8's implementation performs the assignment but always returns false.
    MEL.set_material_instance_texture_parameter_value(instance,semantic,tex)
parameters={'NormalStrength':.9,'DryRoughnessBias':0.0,'ScabRoughnessBias':.02,
            'WoundWetness':.8,'DrySpecular':.25,'WetSpecular':.34}
for key,value in parameters.items():
    MEL.set_material_instance_scalar_parameter_value(instance,key,value)
MEL.set_material_instance_vector_parameter_value(instance,'SkinTint',u.LinearColor(1.0,.985,.97,1))
MEL.set_material_instance_vector_parameter_value(instance,'ClothTint',u.LinearColor(1.04,1.04,1.05,1))
MEL.update_material_instance(instance)
LIB.set_metadata_tag(instance,'Mutant3.SurfaceRevision','SurfacePolish20260923')
save(instance)
state['material']={'asset':instance.get_path_name(),'parent':MASTER,'parameters':parameters}
record()

options=u.FbxImportUI()
options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True
options.import_mesh=True
options.import_animations=False
options.import_materials=False
options.import_textures=False
options.create_physics_asset=False
options.skeleton=skeleton
data=options.skeletal_mesh_import_data
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
data.set_editor_property('use_t0_as_ref_pose',False)
data.set_editor_property('update_skeleton_reference_pose',False)
data.set_editor_property('convert_scene_unit',True)
task=u.AssetImportTask()
task.filename=str(ROOT/'SK_Mutant3_Claw.fbx')
task.destination_name='SK_Mutant3_Claw'
task.destination_path='/Game/Monsters/Mutant3Meshy/KhaimeraV2'
task.options=options
task.automated=True
task.save=False
task.replace_existing=True
task.replace_existing_settings=True
cvar='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(cvar)
u.SystemLibrary.execute_console_command(None,cvar+' 0')
try:
    TOOLS.import_asset_tasks([task])
finally:
    u.SystemLibrary.execute_console_command(None,cvar+' '+str(previous))
if not task.imported_object_paths: raise RuntimeError('Mesh import returned no asset')
mesh=load(MESH)
slots[0].material_interface=instance
mesh.set_editor_property('materials',slots)
mesh.set_editor_property('physics_asset',physics)
build=SUB.get_lod_build_settings(mesh,0)
build.recompute_normals=False
build.recompute_tangents=True
build.use_mikk_t_space=True
build.use_full_precision_u_vs=True
SUB.set_lod_build_settings(mesh,0,build)
if not u.Mutant3.repair_surface_binding(mesh):
    raise RuntimeError('Cannot rebuild Mutant3 source/render section and UV streaming data')
LIB.set_metadata_tag(mesh,'Mutant3.SurfaceRevision','SurfacePolish20260923')
save(mesh)
state['after']={'uv_density':uv_info(mesh),'build_settings':str(build),
                'material':instance.get_path_name(),'skeleton':mesh.skeleton.get_path_name()}
state['state']='Four capped detail textures, material instance, and mesh normals/streaming data saved'
record()
u.log('MUTANT3_SURFACE_POLISH_SAVED '+str(REPORT))
