"""Save the independent Eagle Talon models and the two reference appearances."""
import json
import runpy
from pathlib import Path
import unreal as u

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
ART = HERE/'Art'
ROOT = '/Game/Weapons/ForgedSteelGreatsword20261120/EagleTalonGuard/V1'
if (Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()!=PROJECT or
        '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower()):
    raise RuntimeError('Run in the FPSGAME background Python commandlet.')

EL,ML = u.EditorAssetLibrary,u.MaterialEditingLibrary
tools = u.AssetToolsHelpers.get_asset_tools()
import_asset = runpy.run_path(str(HERE.parent/'CommonMods/install_legendary_blade.py'))['import_asset']
graph = runpy.run_path(str(PROJECT/'SourceAssets/KukriRefinement20261027/hanging_material.py'))
node,wire,out = (graph[k] for k in ('node','link','out'))
saved = []


def save(asset):
    if not asset or not EL.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+str(asset))
    saved.append(asset.get_path_name())


def make_asset(name,cls,factory):
    path = ROOT+'/'+name
    return u.load_asset(path) if EL.does_asset_exist(path) else tools.create_asset(name,ROOT,cls,factory)


def create_metal():
    mat = make_asset('M_EagleTalon_ForgedSteel',u.Material,u.MaterialFactoryNew())
    ML.delete_all_material_expressions(mat)
    mat.set_editor_properties({'used_with_nanite':True,'tangent_space_normal':True,'two_sided':False})
    channels = {}
    for tag,compression,sampler in [
        ('BaseColor','TC_DEFAULT','SAMPLERTYPE_COLOR'),('ORM','TC_MASKS','SAMPLERTYPE_MASKS'),
        ('Normal','TC_NORMALMAP','SAMPLERTYPE_NORMAL'),('IceMask','TC_MASKS','SAMPLERTYPE_MASKS')]:
        name = 'T_EagleTalon_'+tag
        tex = import_asset(ART/(name+'.png'),ROOT,name)
        tex.set_editor_properties({'srgb':tag=='BaseColor',
            'compression_settings':getattr(u.TextureCompressionSettings,compression),
            'lod_group':u.TextureGroup.TEXTUREGROUP_WEAPON})
        if tag=='Normal':
            tex.set_editor_property('flip_green_channel',True)
        save(tex)
        channels[tag] = node(mat,u.MaterialExpressionTextureSample,texture=tex,
                             sampler_type=getattr(u.MaterialSamplerType,sampler))
    front = node(mat,u.MaterialExpressionSubstrateShadingModels,
                 shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for tag,ch,pin,prop in (('BaseColor','RGB','BaseColor','BASE_COLOR'),
                            ('ORM','G','Roughness','ROUGHNESS'),('ORM','B','Metallic','METALLIC'),
                            ('Normal','RGB','Normal','NORMAL')):
        wire(channels[tag],ch,front,pin)
        out(channels[tag],ch,getattr(u.MaterialProperty,'MP_'+prop))
    out(channels['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    strength = node(mat,u.MaterialExpressionScalarParameter,parameter_name='IceStrength',default_value=0.)
    tint = node(mat,u.MaterialExpressionVectorParameter,parameter_name='IceColor',
                default_value=u.LinearColor(.36,.71,1.,1.))
    amount = node(mat,u.MaterialExpressionMultiply)
    wire(channels['IceMask'],'R',amount,'A')
    wire(strength,'',amount,'B')
    emissive = node(mat,u.MaterialExpressionMultiply)
    wire(tint,'RGB',emissive,'A')
    wire(amount,'',emissive,'B')
    wire(emissive,'',front,'Emissive Color')
    out(emissive,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    out(front,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    ML.layout_material_expressions(mat)
    if ML.recompile_material(mat):
        raise RuntimeError('Failed to compile Eagle Talon steel')
    save(mat)
    return mat


mat = create_metal()
lit = make_asset('MI_EagleTalon_Ice',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
ML.set_material_instance_parent(lit,mat)
ML.set_material_instance_scalar_parameter_value(lit,'IceStrength',4.5)
ML.update_material_instance(lit)
save(lit)
seat_path = json.loads((HERE.parent/'CommonMods/blade_materials.json').read_text(encoding='utf8'))['base']
seat_mat = u.load_asset(seat_path)
if not seat_mat:
    raise RuntimeError('Missing original blade seat material')
charge_path = ROOT.rsplit('/',1)[0]+'/GuardCharge/M_EagleTalon_GuardCharge'
metal = u.load_asset(charge_path) if EL.does_asset_exist(charge_path) else mat
surfaces = {'M_ForgedSteelGreatsword_Surface_V1':seat_mat,'M_EagleTalon_ForgedSteel':metal}
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
opt = u.FbxImportUI()
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh = True
opt.import_as_skeletal = opt.import_animations = opt.import_materials = opt.import_textures = False
data = opt.static_mesh_import_data
data.combine_meshes = data.build_nanite = True
data.generate_lightmap_u_vs = data.auto_generate_collision = False
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
meshes = {}
for name,info in json.loads((ART/'exports.json').read_text(encoding='utf8')).items():
    mesh = import_asset(ART/(name+'.fbx'),ROOT,name,opt)
    slots = [str(slot.material_slot_name) for slot in mesh.static_materials]
    if set(slots)!=set(surfaces):
        raise RuntimeError('Unexpected material slots on '+name+': '+str(slots))
    for i,slot in enumerate(slots):
        mesh.set_material(i,surfaces[slot])
    nano = mesh.get_editor_property('nanite_settings')
    nano.enabled = nano.explicit_tangents = True
    nano.fallback_target = u.NaniteFallbackTarget.PERCENT_TRIANGLES
    nano.fallback_percent_triangles = min(1.,54000/info['triangles'])
    mesh.set_editor_property('nanite_settings',nano)
    save(mesh)
    meshes[name] = dict(zip(slots,[mesh.get_material(i).get_path_name() for i in range(len(slots))]))
(ART/'import_receipt.json').write_text(json.dumps({'assets':saved,'meshes':meshes,
    'ice_material':lit.get_path_name()},indent=2)+'\n',encoding='utf8')
print('EAGLE_TALON_MODEL_SAVED',len(saved),flush=True)
