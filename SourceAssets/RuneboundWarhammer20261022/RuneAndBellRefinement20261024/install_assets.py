"""Import the modeled Final Toll module and save its physical and energy materials."""
import json
import re
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
MODEL=P.parent/'FinalTollHammerHeadV2'
D='/Game/Weapons/RuneboundWarhammer20261022/FinalTollV2'
A=u.AssetToolsHelpers.get_asset_tools()
E=u.EditorAssetLibrary
L=u.MaterialEditingLibrary
TAG='RuneboundFinalTollOwner'
OWNER='RuneAndBellRefinement20261024'
receipt={'complete':False,'assets':[],'tested':False,'editor_ui_started':False}


def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')


def save(asset):
    E.set_metadata_tag(asset,TAG,OWNER)
    if not E.save_loaded_asset(asset,False):
        raise RuntimeError('Cannot save '+asset.get_path_name())
    if asset.get_path_name() not in receipt['assets']:
        receipt['assets'].append(asset.get_path_name())
    record()
    return asset


def existing(name):
    path=D+'/'+name
    asset=u.load_asset(path) if E.does_asset_exist(path) else None
    if asset and E.get_metadata_tag(asset,TAG)!=OWNER:
        raise RuntimeError('Preserve unowned package '+path)
    return asset


def node(mat,cls,**props):
    result=L.create_material_expression(mat,cls)
    for key,value in props.items():
        result.set_editor_property(key,value)
    return result


def wire(src,dst,pin,out=''):
    if not L.connect_material_expressions(src,out,dst,pin):
        raise RuntimeError('Cannot wire '+str(pin))


def constant(mat,value):
    return node(mat,u.MaterialExpressionConstant,r=value)


def vector(mat,value):
    return node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1))


def binary(mat,kind,a,b):
    result=node(mat,kind)
    wire(a,result,'A')
    wire(b,result,'B')
    return result


def material(name):
    m=existing(name) or A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
    if not m:
        raise RuntimeError('Cannot create material '+name)
    L.delete_all_material_expressions(m)
    m.set_editor_property('used_with_skeletal_mesh',False)
    m.set_editor_property('used_with_nanite',True)
    m.set_editor_property('two_sided',False)
    return m


def surface(mat,inputs):
    substrate=node(mat,u.MaterialExpressionSubstrateShadingModels)
    names={str(n).replace(' ','').lower():str(n) for n in L.get_material_expression_input_names(substrate)}
    legacy={'basecolor':u.MaterialProperty.MP_BASE_COLOR,'metallic':u.MaterialProperty.MP_METALLIC,
            'roughness':u.MaterialProperty.MP_ROUGHNESS,'normal':u.MaterialProperty.MP_NORMAL,
            'emissivecolor':u.MaterialProperty.MP_EMISSIVE_COLOR,'opacity':u.MaterialProperty.MP_OPACITY,
            'specular':u.MaterialProperty.MP_SPECULAR}
    for key,value in inputs.items():
        source,output=value if isinstance(value,tuple) else (value,'')
        if key not in names:
            raise RuntimeError('Missing substrate pin '+key+' in '+str(names))
        wire(source,substrate,names[key],output)
        if key in legacy:
            L.connect_material_property(source,output,legacy[key])
    if not L.connect_material_property(substrate,'',u.MaterialProperty.MP_FRONT_MATERIAL):
        raise RuntimeError('Cannot connect Substrate surface')
    L.layout_material_expressions(mat)
    errors=L.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compile failed '+mat.get_path_name()+': '+str(errors))
    return save(mat)


def energy_parameters(mat,awake_scale,impact_scale,base):
    tint=node(mat,u.MaterialExpressionVectorParameter,parameter_name='EnergyTint',
              default_value=u.LinearColor(1,.64,.22,1))
    awake=node(mat,u.MaterialExpressionScalarParameter,parameter_name='RuneAwake',default_value=0.)
    impact=node(mat,u.MaterialExpressionScalarParameter,parameter_name='RuneImpact',default_value=0.)
    power=binary(mat,u.MaterialExpressionAdd,
        binary(mat,u.MaterialExpressionMultiply,awake,constant(mat,awake_scale)),
        binary(mat,u.MaterialExpressionAdd,constant(mat,base),
            binary(mat,u.MaterialExpressionMultiply,impact,constant(mat,impact_scale))))
    return tint,binary(mat,u.MaterialExpressionMultiply,tint,power)


project=Path(u.Paths.project_dir()).resolve()
if project not in (ROOT,P/'AuthorHost'):
    raise RuntimeError('Wrong authoring project '+str(project))
record()
textures={}
for suffix in ('BaseColor','ORM','Normal'):
    name='T_FinalToll_'+suffix
    texture=existing(name)
    if not texture:
        task=u.AssetImportTask()
        task.filename=str(MODEL/'Textures'/(name+'.png'))
        task.destination_path=D
        task.destination_name=name
        task.automated=True
        task.save=False
        A.import_asset_tasks([task])
        texture=u.load_asset(D+'/'+name)
    if not texture:
        raise RuntimeError('Cannot import '+name)
    texture.set_editor_property('srgb',suffix=='BaseColor')
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if suffix=='Normal'
        else u.TextureCompressionSettings.TC_MASKS if suffix=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON)
    texture.set_editor_property('never_stream',False)
    texture.set_editor_property('max_texture_size',4096)
    if suffix=='Normal':
        texture.set_editor_property('flip_green_channel',True)
    textures[suffix]=save(texture)

materials={}
m=material('M_FinalToll_PBR_Surface')
color=node(m,u.MaterialExpressionTextureSample,texture=textures['BaseColor'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
orm=node(m,u.MaterialExpressionTextureSample,texture=textures['ORM'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
normal=node(m,u.MaterialExpressionTextureSample,texture=textures['Normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
L.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
materials[m.get_name()]=surface(m,{'basecolor':color,'roughness':(orm,'G'),'metallic':(orm,'B'),'normal':normal})

m=material('M_FinalToll_FineInlay_Brass')
materials[m.get_name()]=surface(m,{'basecolor':vector(m,(.36,.22,.085)),
    'metallic':constant(m,.98),'roughness':constant(m,.30)})

m=material('M_FinalToll_Rune_Energy')
tint,glow=energy_parameters(m,5.,9.,.25)
materials[m.get_name()]=surface(m,{'basecolor':binary(m,u.MaterialExpressionMultiply,tint,constant(m,.06)),
    'metallic':constant(m,0.),'roughness':constant(m,.25),'emissivecolor':glow})

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
name='SM_RuneboundWarhammer_FinalTollHammerHeads_V2'
mesh=existing(name)
if not mesh:
    opt=u.FbxImportUI()
    opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True
    opt.import_as_skeletal=False
    opt.import_materials=False
    opt.import_textures=False
    opt.import_animations=False
    data=opt.static_mesh_import_data
    data.combine_meshes=True
    data.auto_generate_collision=False
    data.generate_lightmap_u_vs=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask()
    task.filename=str(MODEL/'Export'/(name+'.fbx'))
    task.destination_path=D
    task.destination_name=name
    task.automated=True
    task.save=False
    task.options=opt
    A.import_asset_tasks([task])
    mesh=u.load_asset(D+'/'+name)
if not mesh:
    raise RuntimeError('Cannot import Final Toll static mesh')
for index,slot in enumerate(mesh.get_editor_property('static_materials')):
    key=re.sub(r'(?:[._]\d{3})+$','',str(slot.material_slot_name))
    if key not in materials:
        raise RuntimeError('Unknown material slot '+key)
    mesh.set_material(index,materials[key])
# This near-view module has true translucent optical shells in its four material
# sections. Keep the authored conventional geometry instead of hiding those
# sections with an incompatible all-Nanite route.
nanite=mesh.get_editor_property('nanite_settings')
nanite.enabled=True
mesh.set_editor_property('nanite_settings',nanite)
save(mesh)
receipt.update(complete=True,mesh=mesh.get_path_name(),material_slots=list(materials),
    native_triangles=99000,texture_resolution=4096,animation_assets_modified=0,
    energy_parameters=['RuneAwake','RuneImpact','EnergyTint'],nanite=True,
    nanite_reason='Opaque rigid bell-cage head with explicit open geometry')
record()
print('FINAL_TOLL_ASSETS_SAVED '+json.dumps(receipt,ensure_ascii=False))


exec(compile((P/"install_runes_icons.py").read_text("utf-8"),str(P/"install_runes_icons.py"),"exec"))
